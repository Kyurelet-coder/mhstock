import urllib.request
import ssl

url='https://mhcollector.com/category/characters/ghouls/'
req=urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
ctx=ssl.create_default_context()
ctx.check_hostname=False
ctx.verify_mode=ssl.CERT_NONE
with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
    data=resp.read().decode('utf-8', 'ignore')
print(data[:8000])
