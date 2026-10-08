import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import gen_stubs
import work


def ledger():
    con = sqlite3.connect(':memory:')
    con.row_factory = sqlite3.Row
    con.executescript(work.SCHEMA)
    con.execute("INSERT INTO tu(id,status) VALUES('Vendor','blocked')")
    con.execute("INSERT INTO func(name,tu_id,status) VALUES('Vendor::API','Vendor','todo')")
    con.execute("INSERT INTO func(name,tu_id,status) VALUES('Vendor::Recovered','Vendor','reviewed')")
    return con


def test_external_survives_local_status_and_is_never_trap_stubbed(monkeypatch):
    con = ledger()
    monkeypatch.setattr(work, 'sync_status', lambda con: None)
    work.set_tu(con, 'Vendor', 'external', notes='Checked-in vendor source')
    assert gen_stubs.resolved_names(con) == {'Vendor::API', 'Vendor::Recovered'}
    assert con.execute("SELECT status FROM func WHERE name='Vendor::Recovered'").fetchone()[0] == 'reviewed'
    with pytest.raises(SystemExit, match='explicitly unblock'):
        work.set_tu(con, 'Vendor', 'in_progress', owner='worker')
    work.set_tu(con, 'Vendor', 'todo')
    assert con.execute("SELECT status FROM func WHERE name='Vendor::API'").fetchone()[0] == 'todo'


def test_external_cannot_take_over_local_compiled_work(monkeypatch):
    con = ledger()
    monkeypatch.setattr(work, 'sync_status', lambda con: None)
    con.execute("UPDATE tu SET status='compiled',owner='worker' WHERE id='Vendor'")
    with pytest.raises(SystemExit, match='active or compiled'):
        work.set_tu(con, 'Vendor', 'external', notes='Wrong provider')
    assert con.execute("SELECT status FROM tu WHERE id='Vendor'").fetchone()[0] == 'compiled'
