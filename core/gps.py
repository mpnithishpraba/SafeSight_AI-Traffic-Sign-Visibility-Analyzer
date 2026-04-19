import threading
import time
import asyncio
import geocoder

try:
    import winreg
    HAS_WINREG = True
except ImportError:
    HAS_WINREG = False

try:
    from winrt.windows.devices.geolocation import Geolocator, GeolocationAccessStatus
    HAS_WINRT = True
except ImportError:
    HAS_WINRT = False

class GPSProvider:
    def __init__(self):
        self.lat, self.lon = 0.0, 0.0
        self._active = False
        self.gps_enabled = True

    def start(self):
        self._active = True
        threading.Thread(target=self._loop, daemon=True).start()

    def stop(self):
        self._active = False

    def is_windows_location_enabled(self):
        if HAS_WINREG:
            try:
                # Check system-wide location setting
                k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\CapabilityAccessManager\ConsentStore\location")
                v, _ = winreg.QueryValueEx(k, "Value")
                winreg.CloseKey(k)
                if v == "Deny":
                    return False
            except Exception:
                pass
        return True

    def _fetch_winrt(self):
        async def _get():
            try:
                req = await Geolocator.request_access_async()
                if req == GeolocationAccessStatus.ALLOWED:
                    locator = Geolocator()
                    pos = await asyncio.wait_for(locator.get_geoposition_async(), timeout=5.0)
                    return pos.coordinate.latitude, pos.coordinate.longitude, True
            except Exception:
                pass
            return None, None, False
        try:
            return asyncio.run(_get())
        except Exception:
            return None, None, False

    def _fetch_ip(self):
        try:
            g = geocoder.ip('me')
            if g.ok and g.latlng:
                return g.latlng[0], g.latlng[1], True
        except Exception:
            pass
        return None, None, False

    def _loop(self):
        while self._active:
            enabled = self.is_windows_location_enabled()
            self.gps_enabled = enabled
            
            if enabled:
                lat, lon, success = None, None, False
                if HAS_WINRT:
                    lat, lon, success = self._fetch_winrt()
                    
                if success:
                    self.lat, self.lon = lat, lon
                else:
                    # Fallback to IP geolocation if true GPS module fails
                    lat, lon, success = self._fetch_ip()
                    if success:
                        self.lat, self.lon = lat, lon
            else:
                # Disabled in OS settings
                pass

            time.sleep(2)

    def coords(self):
        return round(self.lat, 6), round(self.lon, 6)

    def coords_str(self):
        return f"{self.lat:.6f},{self.lon:.6f}"
