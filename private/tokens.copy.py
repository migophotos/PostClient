# 0. rename this file to token.py

# 1. Register new telegram account with name and phone
APP_OWNER = ''
APP_OWNER_PHONE = '+972'
APP_OWNER_USERNAME = '@'

"""
Login to your Telegram account with the phone number of the developer account to use.
https://my.telegram.org/

Click under API Development tools.
A Create new application window will appear. Fill in your application details. There is no need to enter any URL, 
and only the first two fields (App title and Short name) can currently be changed later.
Click on Create application at the end. 
ATTENTION: Remember that your API hash is secret and Telegram won’t let you revoke it. Don’t post it anywhere!
"""
# 1. go to https://my.telegram.org/apps and create new app for this new account
# 2. fill fields App title и Short name, click on «Create application» и store here: api_id и api_hash.
APP_TITLE: str = 'enter app title'
APP_NAME: str = 'enter app short name'
API_ID: int = 0
API_HASH: str = ''

# 3. Create a new channel (public or private) that will receive service messages
# Use @username_to_id_bot bot to find its id and store channel id into APP_CHANNEL_ID
# Change APP_CHANNEL_NAME and APP_CHANNEL_LINK with correspondent info from you channel also
APP_CHANNEL_ID: int = -100        # special messages will be sent to this channel
APP_CHANNEL_NAME: str = ''   # special channel name, '@username_to_id_bot' returns its id
APP_CHANNEL_LINK = ''                   # not in use, just for memory

# 4. Save the path to the database in this variable
APP_DATABASE: str = f'./database/{APP_NAME}.db'

# 5. start conversation with @username_to_id_bot and find the text, started with 'P.S. Your ID:'
# copy the following number to this var
APP_OWNER_ID: int = 0

"""
start telegram post client: python3 postclient.py and authorize (enter your phone number and code that 
telegram will send you). This is one time process that creates {APP_NAME}.session file in your script directory

send message 'help' to APP_CHANNEL_NAME channel from your new telegram account for get information about using your 
telegram post client! Enjoy! 
"""
