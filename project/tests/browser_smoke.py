"""Real browser integration test; starts an isolated server and score file.
Install playwright + Chromium first. Run from the repository root.
"""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import networkx as nx
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
with tempfile.TemporaryDirectory() as directory:
    with socket.socket() as sock:
        sock.bind(('127.0.0.1', 0)); port = sock.getsockname()[1]
    config = Path(directory)/'config.toml'
    storage = Path(directory)/'scores.json'
    config.write_text(f'[eel]\nopen_browser_on_start=false\nport={port}\n[game]\nduration_seconds=30\nstorage_file="{storage}"\n')
    process = subprocess.Popen([sys.executable,str(ROOT/'project/run.py'),'--config',str(config)],cwd=ROOT,stdout=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                with socket.create_connection(('127.0.0.1',port),timeout=.1): break
            except OSError: time.sleep(.1)
        with sync_playwright() as p:
            browser=p.chromium.launch(args=['--enable-unsafe-swiftshader'])
            page=browser.new_page(viewport={'width':1440,'height':900}, has_touch=True, color_scheme='light')
            errors=[]; puzzles=[]; external=[]
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('request',lambda request: external.append(request.url) if not request.url.startswith(f'http://localhost:{port}') else None)
            def frame(payload):
                data=json.loads(payload)
                result=data.get('value',{})
                if isinstance(result,dict) and 'puzzle' in result: puzzles.append(result['puzzle'])
            page.on('websocket',lambda ws:ws.on('framereceived',frame))
            page.goto(f'http://localhost:{port}',wait_until='networkidle')
            expect(page.locator('#motif-name')).not_to_have_text('Motif', timeout=20000)
            expect(page.locator('#next')).to_be_enabled(timeout=20000)
            page.evaluate("async()=>{window.graph=(await import('/js/index.js')).graph}")
            assert page.evaluate('graph.graphData().nodes.every(n=>n.x===n.fx && n.y===n.fy && n.z===n.fz)')
            assert {n['element'] for n in puzzles[-1]['nodes']} == {'C','O','H','N'}
            assert page.evaluate("new Set(graph.graphData().nodes.map(n=>graph.nodeColor()(n))).size") == 4
            expect(page.locator('#graph-network .atom-labels')).to_have_count(1)
            expect(page.locator('.atom-legend')).to_contain_text('Carbone')
            expect(page.locator('.atom-legend')).to_contain_text('liens fictifs')
            page.wait_for_timeout(450)
            # Exercise actual WebGL picking, as well as the accessible controls.
            position=page.evaluate('''() => graph.graphData().nodes
                .slice().sort((a,b)=>b.z-a.z).map(n=>graph.graph2ScreenCoords(n.x,n.y,n.z))
                .find(p=>p.x>40 && p.x<graph.width()-210 && p.y>50 && p.y<graph.height()-60)''')
            box=page.locator('#graph-network').bounding_box()
            page.mouse.move(box['x']+position['x'],box['y']+position['y'])
            page.mouse.click(box['x']+position['x'],box['y']+position['y'])
            expect(page.locator('#selection')).to_contain_text('1 /')
            # Theme changes recolor WebGL and keep camera/selection intact.
            camera_before_theme=page.evaluate('graph.cameraPosition()')
            page.locator('#theme-toggle').click()
            expect(page.locator('html')).to_have_attribute('data-theme','dark')
            expect(page.locator('#theme-toggle')).to_have_attribute('aria-pressed','true')
            assert page.evaluate('graph.backgroundColor()') == '#211a2b'
            assert page.evaluate("graph.graphData().nodes.filter(n=>graph.nodeColor()(n)==='#6ee7a0').length") == 1
            assert page.evaluate('graph.cameraPosition()') == camera_before_theme
            page.screenshot(path='/tmp/spotted-dark.png',full_page=True)
            page.locator('#theme-toggle').click()
            assert page.evaluate('graph.backgroundColor()') == '#f4f1f8'
            expect(page.locator('#selection')).to_contain_text('1 /')
            # Undo works on empty space and must not pan the camera.
            camera_before_undo=page.evaluate('graph.cameraPosition()')
            page.mouse.click(box['x']+25,box['y']+25,button='right')
            expect(page.locator('#selection')).to_contain_text('0 /')
            assert page.evaluate('graph.cameraPosition()') == camera_before_undo
            # Immediate clicks don't need a previous hover/raycast frame.
            for _ in range(4):
                page.mouse.click(box['x']+position['x'],box['y']+position['y'])
                expect(page.locator('#selection')).to_contain_text('1 /')
                page.mouse.click(box['x']+position['x'],box['y']+position['y'])
                expect(page.locator('#selection')).to_contain_text('0 /')
            # A near miss just beyond the visible sphere still selects it.
            near=page.evaluate("""() => {
                const camera=graph.camera();
                const nodes=graph.graphData().nodes.map(n=>{
                    const p=graph.graph2ScreenCoords(n.x,n.y,n.z);
                    const depth=-camera.position.clone().set(n.x,n.y,n.z).applyMatrix4(camera.matrixWorldInverse).z;
                    const radius=graph.nodeRelSize()*Math.cbrt(graph.nodeVal())*graph.height()/(2*Math.tan(camera.fov*Math.PI/360)*depth);
                    return {...p,radius,id:n.id};
                });
                return nodes.map(n=>({...n,x:n.x+n.radius+3})).find(p=>
                    p.x>40 && p.x<graph.width()-210 && p.y>50 && p.y<graph.height()-60 &&
                    nodes.every(n=>n.id===p.id || Math.hypot(n.x-p.x,n.y-p.y)>n.radius+25));
            }""")
            assert near is not None
            page.mouse.click(box['x']+near['x'],box['y']+near['y'])
            expect(page.locator('#selection')).to_contain_text('1 /')
            page.mouse.click(box['x']+25,box['y']+25,button='right')
            # Small hand movement is a click; a real drag isn't.
            page.mouse.move(box['x']+position['x'],box['y']+position['y'])
            page.mouse.down(); page.mouse.move(box['x']+position['x']+3,box['y']+position['y']+2); page.mouse.up()
            expect(page.locator('#selection')).to_contain_text('1 /')
            page.mouse.click(box['x']+25,box['y']+25,button='right')
            page.locator('#recenter').click()
            page.wait_for_timeout(100)
            page.touchscreen.tap(box['x']+position['x'],box['y']+position['y'])
            expect(page.locator('#selection')).to_contain_text('1 /')
            page.locator('#clear').click()
            camera=page.evaluate('graph.cameraPosition()')
            page.mouse.move(box['x']+100,box['y']+150); page.mouse.down()
            page.mouse.move(box['x']+200,box['y']+200,steps=15); page.mouse.up()
            page.wait_for_timeout(300)
            assert page.evaluate('graph.cameraPosition()') != camera
            expect(page.locator('#selection')).to_contain_text('0 /')
            assert page.evaluate('graph.graphData().nodes.every(n=>n.x===n.fx && n.y===n.fy && n.z===n.fz)')
            page.locator('#recenter').click(); page.wait_for_timeout(450)
            assert page.evaluate('graph.graphData().nodes.map(n=>graph.graph2ScreenCoords(n.x,n.y,n.z)).every(p=>p.x>0 && p.x<graph.width() && p.y>0 && p.y<graph.height())')
            assert page.locator('#graph-network').bounding_box()['height'] >= 900 * .75
            assert page.locator('#validate').bounding_box()['y'] + page.locator('#validate').bounding_box()['height'] <= 900
            page.screenshot(path='/tmp/spotted-desktop.png',full_page=True)
            expect(page.locator('.keyboard, #node-buttons')).to_have_count(0)

            def click_node(node_id):
                # Orient the actual scene so the requested node is unobscured,
                # then select through the real pointer path (no test-only API).
                point = page.evaluate("""id => {
                    const n=graph.graphData().nodes.find(n=>n.id===id);
                    const camera=graph.camera();
                    const axes=[[0,0,1],[1,0,1],[-1,1,1],[0,-1,1],[1,1,-1]];
                    for(const [dx,dy,dz] of axes) {
                        graph.controls().reset(); camera.up.set(0,1,0);
                        graph.cameraPosition({x:n.x+dx*350,y:n.y+dy*350,z:n.z+dz*350},n,0);
                        graph.controls().update(); camera.updateMatrixWorld();
                        const point=graph.graph2ScreenCoords(n.x,n.y,n.z);
                        const clear=graph.graphData().nodes.every(other=>{
                            if(other.id===id) return true;
                            const q=graph.graph2ScreenCoords(other.x,other.y,other.z);
                            const depth=-camera.position.clone().set(other.x,other.y,other.z).applyMatrix4(camera.matrixWorldInverse).z;
                            if(depth<=0) return true;
                            const radius=graph.nodeRelSize()*Math.cbrt(graph.nodeVal())*graph.height()/(2*Math.tan(camera.fov*Math.PI/360)*depth);
                            return Math.hypot(q.x-point.x,q.y-point.y)>radius+12;
                        });
                        if(clear) return point;
                    }
                    return null;
                }""", node_id)
                assert point is not None, node_id
                bounds=page.locator('#graph-network').bounding_box()
                page.mouse.click(bounds['x']+point['x'],bounds['y']+point['y'])

            def selected_nodes():
                return page.evaluate("graph.graphData().nodes.filter(n=>graph.nodeColor()(n)==='#159447').map(n=>n.id)")

            click_node(0); click_node(1); click_node(0); click_node(0)
            page.mouse.click(box['x']+25,box['y']+25,button='right')
            assert selected_nodes()==[1]
            page.mouse.click(box['x']+25,box['y']+25,button='right')
            expect(page.locator('#selection')).to_contain_text('0 /')
            page.mouse.click(box['x']+25,box['y']+25,button='right')
            expect(page.locator('#selection')).to_contain_text('0 /')

            def solve(timed=False):
                view=puzzles[-1]
                g=nx.Graph(); g.add_nodes_from(n['id'] for n in view['nodes']); g.add_edges_from((e['source'],e['target']) for e in view['links'])
                motif=nx.Graph(view['motif']['edges'])
                found=next(nx.algorithms.isomorphism.GraphMatcher(g,motif).subgraph_isomorphisms_iter())
                previous=len(puzzles)
                score=int(page.locator('#score').inner_text())
                for node in found: click_node(node)
                if timed:
                    expect(page.locator('#score')).to_have_text(str(score+1))
                    expect(page.locator('#next')).to_be_enabled()
                    assert len(puzzles)==previous+1
                    expect(page.locator('#selection')).to_contain_text('0 /')
                    expect(page.locator('#validate')).to_be_hidden()
                else:
                    assert page.evaluate("graph.graphData().links.filter(l=>graph.linkWidth()(l)>3).length") == len(view['motif']['edges'])
                    # Discovery still waits for explicit validation and Next.
                    assert len(puzzles)==previous
                    expect(page.locator('#score')).to_have_text(str(score))
                    page.locator('#validate').click()
                    expect(page.locator('#status')).to_contain_text('Repéré en')
                return found

            # Wrong full selection, then clear and solve through actual node clicks.
            view=puzzles[-1]
            from itertools import combinations
            g=nx.Graph([(e['source'],e['target']) for e in view['links']]); motif=nx.Graph(view['motif']['edges'])
            wrong=next(c for c in combinations(g,len(motif)) if not nx.is_isomorphic(g.subgraph(c),motif))
            for node in wrong: click_node(node)
            page.locator('#validate').click()
            expect(page.locator('#status')).to_contain_text('Pas encore')
            page.locator('#clear').click()
            solve(); expect(page.locator('#score')).to_have_text('1')
            expect(page.locator('#validate')).to_be_disabled()
            page.screenshot(path='/tmp/spotted-solved.png',full_page=True)
            previous=len(puzzles)
            page.locator('#next').click()
            expect(page.locator('#next')).to_be_enabled()
            assert len(puzzles)>previous
            expect(page.locator('#score')).to_have_text('1')
            solve(); expect(page.locator('#score')).to_have_text('2')
            page.locator('#finish').click(); expect(page.locator('#result')).to_be_visible()
            page.locator('#name').fill('<Lynx & Co>')
            page.locator('#save-form button').click()
            expect(page.locator('#save-status')).to_contain_text('enregistrée')
            page.locator('#close-result').click(); page.locator('#gallery-tab').click()
            expect(page.locator('.card')).to_have_count(1)
            expect(page.locator('.card strong')).to_contain_text('<Lynx & Co>')
            page.locator('#theme-toggle').click()
            page.locator('.card').click(); expect(page.locator('#replay-dialog canvas').first).to_be_visible()
            assert page.locator('#replay-dialog').evaluate('(el)=>getComputedStyle(el).backgroundColor') == 'rgb(43, 34, 53)'
            page.screenshot(path='/tmp/spotted-dark-gallery.png',full_page=True)
            expect(page.locator('#replay-graph .atom-labels')).to_have_count(1)
            page.locator('#close-replay').click()
            expect(page.locator('#replay-graph .atom-labels')).to_have_count(0)
            page.locator('#theme-toggle').click()
            # Timed session, server deadline, score save, and ranking.
            page.locator('#mode').select_option('timed'); page.locator('#start').click()
            expect(page.locator('#score')).to_have_text('0')
            expect(page.locator('#next')).to_be_enabled()
            expect(page.locator('#mode')).to_be_disabled()
            expect(page.locator('#next')).to_have_text('Passer (−10 s)')
            previous=len(puzzles)
            before_time=page.locator('#timer').inner_text()
            page.locator('#next').click()
            expect(page.locator('#next')).to_be_enabled()
            assert len(puzzles)==previous+1
            after_time=page.locator('#timer').inner_text()
            def time_seconds(text):
                minutes,seconds=map(int,text.split(':'))
                return minutes*60+seconds
            assert 10 <= time_seconds(before_time)-time_seconds(after_time) <= 12
            expect(page.locator('#score')).to_have_text('0')
            # A wrong full selection is checked automatically but stays editable.
            view=puzzles[-1]
            g=nx.Graph([(e['source'],e['target']) for e in view['links']])
            motif=nx.Graph(view['motif']['edges'])
            wrong=next(c for c in combinations(g,len(motif)) if not nx.is_isomorphic(g.subgraph(c),motif))
            previous=len(puzzles)
            for node in wrong: click_node(node)
            expect(page.locator('#status')).to_contain_text('Pas encore')
            assert len(puzzles)==previous
            expect(page.locator('#score')).to_have_text('0')
            page.mouse.click(box['x']+25,box['y']+25,button='right')
            expect(page.locator('#selection')).to_contain_text(f'{len(motif)-1} /')
            page.locator('#clear').click()
            solve(timed=True)
            solve(timed=True)
            # A second skip costs another 10 s; the real timer still expires.
            page.locator('#next').click()
            expect(page.locator('#result')).to_be_visible(timeout=15000)
            expect(page.locator('#validate')).to_be_disabled()
            page.locator('#name').fill('ChronoLynx'); page.locator('#save-form button').click()
            expect(page.locator('#save-status')).to_contain_text('enregistrée')
            page.locator('#close-result').click(); page.locator('#scores-tab').click()
            expect(page.locator('.ranking-row')).to_have_count(1)
            expect(page.locator('.ranking-row')).to_contain_text('ChronoLynx')
            assert len(json.loads(storage.read_text()))==2
            assert all(n['element'] in {'C','O','H','N'} for r in json.loads(storage.read_text()) for n in r['best']['puzzle']['nodes'])
            page.locator('#mode').select_option('free')
            page.locator('#level').select_option('hard')
            page.locator('#start').click()
            expect(page.locator('#next')).to_be_enabled()
            assert len(puzzles[-1]['nodes']) == 60
            assert len(puzzles[-1]['links']) == 90
            assert page.evaluate('graph.graphData().nodes.length') == 60
            page.wait_for_timeout(400)
            page.screenshot(path='/tmp/spotted-hard.png',full_page=True)
            page.locator('#theme-toggle').click()
            page.reload(wait_until='networkidle')
            expect(page.locator('html')).to_have_attribute('data-theme','dark')
            expect(page.locator('#theme-toggle')).to_have_attribute('aria-pressed','true')
            expect(page.locator('.ranking-row')).to_have_count(1)
            page.set_viewport_size({'width':390,'height':844})
            page.wait_for_timeout(450)
            page.screenshot(path='/tmp/spotted-mobile.png',full_page=True)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
            assert not errors,errors
            assert not external,external
            browser.close()
            print('Browser checks passed: fixed 3D, instant/tolerant mouse picking, touch, right-click undo, drag distinction, selection/edges, automatic timed validation and next puzzle, editable wrong answers, skip penalty, timer, persistent dark mode, safe names, gallery 3D, mobile, offline assets.')
    finally:
        process.terminate()
        process.wait(timeout=5)
