"""Local, atomic persistence; never silently overwrite a damaged file."""
import json
import os
from pathlib import Path
import tempfile
from threading import Lock


class Records:
    def __init__(self, path, limit=300):
        self.path, self.limit, self.lock = Path(path), limit, Lock()

    def read(self):
        if not self.path.exists():
            return []
        data = json.loads(self.path.read_text(encoding='utf-8'))
        if not isinstance(data, list) or any(not isinstance(r, dict) or not {'id', 'name', 'score', 'mode', 'level', 'duration', 'best'} <= r.keys() for r in data):
            raise ValueError('Le fichier de scores est endommagé. Il a été préservé.')
        return data

    def add(self, record):
        with self.lock:
            records = self.read()
            if any(r['id'] == record['id'] for r in records):
                return
            records.append(record)
            records = records[-self.limit:]
            self.path.parent.mkdir(parents=True, exist_ok=True)
            name = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent, delete=False) as stream:
                    name = stream.name
                    json.dump(records, stream, ensure_ascii=False)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(name, self.path)
            finally:
                if name and os.path.exists(name):
                    os.unlink(name)
