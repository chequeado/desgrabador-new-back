import requests

api_token = "awnenovd2wulr7t6x8t5cavsdaror4lkdgwg4s1b"
headers = {"Authorization": f"Token {api_token}"}

print("Obteniendo TODOS tus proxies...")
response = requests.get(
    "https://proxy.webshare.io/api/v2/proxy/list/",
    headers=headers,
    params={"mode": "direct", "page_size": 100}
)

if response.status_code == 200:
    data = response.json()
    proxies = data.get('results', [])
    
    print(f"\n✓ Tienes {len(proxies)} proxies disponibles")
    print("\nLista completa para tu .env:")
    print("WEBSHARE_PROXY_LIST=" + ",".join([f"{p['proxy_address']}:{p['port']}" for p in proxies]))
    
    print(f"\nCredenciales (todas usan las mismas):")
    if proxies:
        print(f"WEBSHARE_PROXY_USERNAME={proxies[0]['username']}")
        print(f"WEBSHARE_PROXY_PASSWORD={proxies[0]['password']}")