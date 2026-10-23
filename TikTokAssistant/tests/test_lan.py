"""LAN display listener intentionally omits all POST administration routes."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from overlay_server import create_lan_display_app, is_rfc1918_address


def test_lan_address_validation():
    for ip in ('192.168.1.105', '10.0.0.7', '172.16.2.3', '172.31.100.9'):
        assert is_rfc1918_address(ip)
    for ip in ('127.0.0.1','0.0.0.0','8.8.8.8','172.32.0.1','localhost','', '::1'):
        assert not is_rfc1918_address(ip)


def test_lan_display_has_only_read_only_routes():
    app=create_lan_display_app()
    routes={(route.method, route.resource.canonical) for route in app.router.routes()}
    assert ('GET','/overlay') in routes
    assert ('GET','/ws') in routes
    for route in ('/event','/reset_coins','/test_alert','/config','/stats'):
        assert not any(path==route for _method,path in routes)
    assert not any(method=='POST' for method,_path in routes)
