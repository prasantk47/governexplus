import pyrfc

conn = pyrfc.Connection(
    ashost="10.56.7.4",
    sysnr="01",
    client="100",
    user="PAICHHAP",
    passwd="Pushpa@250582",
    lang="EN"
)
print("Connected!")
conn.call("RFC_PING")
print("RFC_PING OK")
info = conn.call("RFC_SYSTEM_INFO").get("RFCSI_EXPORT", {})
print(f"System: {info.get('RFCSYSID','?')} Release: {info.get('RFCSAPRL','?')}")
users = conn.call("BAPI_USER_GETLIST", MAX_ROWS=0, WITH_USERNAME="*").get("USERLIST", [])
print(f"Total users: {len(users)}")
conn.close()
print("SUCCESS!")
