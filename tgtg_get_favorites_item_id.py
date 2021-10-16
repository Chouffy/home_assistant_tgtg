from tgtg import TgtgClient
# https://github.com/ahivert/tgtg-python

email = "Your TGTG mail"
password = "Your TGTG password"

client = TgtgClient(email=email, password=password)

# toto = client.get_item(item_id=529241)
tgtgReply = client.get_items()

print('  item:')
for item in tgtgReply:
    print('    #', item['display_name'])
    print('    - ', item['item']['item_id'])

input("Press enter to quit ...")