import requests

token = requests.post(
    'http://api.pavel3333.ru/add_wgmods_token.php',
    data = {
        'password' : open('password.txt', 'r').read(),
        'modID'    : input('Please enter the mod ID: ')
    }
).text

if len(token) != 252:
    print token
else:
    open('token', 'wb').write(token)
    print 'Token generated!'
