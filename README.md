# TooGoodToGo items stock as a sensor in Home Assistant

This aim to show the stock of one or multiple [TooGoodToGo](https://toogoodtogo.com/) item using the [tgtg-python](https://github.com/ahivert/tgtg-python) library.
Sensor data can be used afterward to generate notifications, history graphs, ...

## Usage

### Installation via [HACS](https://hacs.xyz/)

1. Search for *TooGoodToGo* in the Integration tab of HACS
1. Click *Install*
1. Install required packages:
  * [Python 3.8](https://www.python.org/downloads/)
  * [tgtg-python](https://github.com/ahivert/tgtg-python) library: In a command line, type `pip install tgtg`
1. Run [this script](./tgtg_get_tokens.py)
  * If your account doesn't have a password, try to reset your password from the app.
1. Paste the result in your `/config/configuration.yaml`.
1. Restart the Home Assistant server

### Configuration option

```yaml
sensor:
- platform: tgtg
  username: 'Your TGTG mail'
  password: 'Your TGTG password'

  # Refresh the stock every 15 minutes
  scan_interval: 900

  # Optional, use defined items ID instead to get your favorites
  item:
    # item_id 1
    - 1234
    # item_id 2
    - 5678

  # Optional, for token-based authentication and to avoid emails at each Home Assistant restart
  access_token: "abc123"
  refresh_token: "abc123"
  user_id: "123"
```

* If your account doesn't have a password, try to reset your password from the app.
* To avoid email, specify `access_token`, `refresh_token` and `user_id`. They can be retrieved using [this script](./tgtg_get_tokens.py)!

### How to get item_id

Check the [tgtg_get_favorites_item_id](./tgtg_get_favorites_item_id.py) script!

1. Set up email/password
1. Run it
1. Copy the full output in the `configuration.yaml` for the `item` section

## Features

Actual:

* Fetch each item stock defined
* Authenticate using email/password or tokens
* Retrieve all favorites instead of a manual list of item_id if no item: are defined

Maybe one day:

* Parse additional available information from the `tgtg` API to Home-Assistant Attributes
