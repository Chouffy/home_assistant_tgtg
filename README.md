# Too Good To Go items stock as a sensor in Home Assistant

This aim to show the stock of one or multiple [Too Good To Go](https://toogoodtogo.com/) item using the [tgtg-python](https://github.com/ahivert/tgtg-python) library.\
Sensor data can be used afterward to generate notifications, history graphs, ... share your best examples in the [Discussion tab](https://github.com/Chouffy/home_assistant_tgtg/discussions)!

## Features

- Fetch each item stock defined
- Authenticate using tokens
- Retrieve all favorites instead of a manual list of item_id if no `item:` are defined
- Retrieve additional information as attributes, if available:
  - Item ID
  - Price and original value
  - Pick-up start and end time
  - Sold-out time
  - Orders placed (if above 0, then below attributes also appear)
    - Total quantity ordered (total from 1 or more orders placed)
    - Pickup window changed (true/false)
    - Cancel-until time
- [Dashboard card example
](https://github.com/Chouffy/home_assistant_tgtg?tab=readme-ov-file#dashboard-card-example)
## Installation

Two steps are required:

1. Get access tokens, either manually or via Docker
1. Install the integration

### 1. Get access tokens

First you'll need to get access tokens for this integration to work.\
This is to be executed outside of Home Assistant, i.e. on your local machine.

#### 1a. Python

1. Install required packages.
   - [Python >=3.8](https://www.python.org/downloads/)
   - [tgtg-python](https://github.com/ahivert/tgtg-python) library: In a command line, type `pip install tgtg>=0.11.0` or `pip install --upgrade tgtg` if you already have it.
1. Run the [tgtg_get_tokens](./tgtg_get_tokens.py) script to get access and refresh token. Save these for later.

#### 1b. Docker

_This is work in progress._

You only need Docker installed. There is no need to clone the repo because Docker can build from an external URL.

```
docker build https://github.com/Chouffy/home_assistant_tgtg.git#main --tag "homeassistant_tgtg_tokens:latest"
docker run --rm -it homeassistant_tgtg_tokens
```

### 2. Installation via [HACS](https://hacs.xyz/)

1. Search for _TooGoodToGo_ in the Integration tab of HACS
1. Click _Install_
1. Copy over the tokens in `/config/configuration.yaml` retrieved in 1.
1. Restart the Home Assistant server
   - ⚠ Each time you add/remove a favorite in the TGTG app, **restart your Home Assistant**. Favorites are only updated at boot!

## Configuration option

```yaml
sensor:
  - platform: tgtg

    # Optional: email so you know which account is used
    email: "Your TGTG mail"

    # Mandatory: tokens for authentication - see the tgtg_get_tokens.py script
    access_token: "abc123"
    refresh_token: "abc123"
    user_id: "123456"
    cookie: "datadome=..."

    # Optional: Refresh the stock every 15 minutes
    scan_interval: 900

    # Optional, use defined items ID instead to get your favorites
    item:
      # item_id 1
      - 1234
      # item_id 2
      - 5678

    # Optional: user agent - by default, the latest one is retrieved from the Google Play store
    #user_agent: "TGTG/22.2.1 Dalvik/2.1.0 (Linux; U; Android 9; SM-G955F Build/PPR1.180610.011)"
```

`access_token`, `refresh_token`, `user_id` and `cookie` can be retrieved using the [tgtg_get_tokens](./tgtg_get_tokens.py) script!

### How to get item_id

Check the [tgtg_get_favorites_item_id](./tgtg_get_favorites_item_id.py) script!

1. Set up email/password
1. Run it
1. Copy the full output in the `configuration.yaml` for the `item` section

## Dashboard card example

Here is an example for a card on your Home Assistant dashboard created by @wallieboy, updated by @Sarnog in https://github.com/Chouffy/home_assistant_tgtg/issues/73 and @tjorim. Support for images was later added by @ov3rk1ll in https://github.com/Chouffy/home_assistant_tgtg/pull/139.\
Make sure you install the custom `auto-entities` and `multiple-entity-row` cards as well.

```yaml
type: custom:auto-entities
card:
  type: entities
  title: TGTG Surprise Bags
filter:
  template: |-
    {% for state in states.sensor if 'sensor.tgtg_' in state.entity_id %}
      {% set entity_id = state.entity_id %}
      {% set state = states(entity_id) %}
      {%- if is_number(state) and state | int > 0 %}
        {% set pickup_start = state_attr(entity_id, 'pickup_start') %}
        {%- if pickup_start is not none -%}
          {{
            {
              'entity': entity_id,
              'name': state_attr(entity_id, 'friendly_name')[5:],
              'type': "custom:multiple-entity-row",
              'unit': false,
              'secondary_info': as_timestamp(pickup_start) | timestamp_custom('Pickup on %d-%m between %H:%M and ', true) + as_timestamp(state_attr(entity_id, 'pickup_end')) | timestamp_custom('%H:%M, € ', true) + state_attr(entity_id, 'item_price')[:-3],
              'image': state_attr(entity_id, 'logo_url'),
              'tap_action': {
                'action': 'url',
                'url_path': state_attr(entity_id, 'item_url')
              }
            }
          }},
        {%- endif -%}
      {%- endif -%}
    {%- endfor %}

```

![image](https://github.com/Chouffy/home_assistant_tgtg/assets/1294876/db2899ac-0023-4c8b-9f61-07e764408e1f)

## Q&A

- It was working before, but now all Too Good To Go sensors are "not available"
  - Try to update your tokens using [the script](https://github.com/Chouffy/home_assistant_tgtg/blob/main/tgtg_get_tokens.py) and restart Home Assistant
- I have a sensor that shows now as unavailable when there's no stock
  - Try add it manually using Item ID - See [this issue](https://github.com/Chouffy/home_assistant_tgtg/issues/18)
- The `tgtg` integration won't start, all my sensors are unavailable and I have a list of manually defined items ID
  - Double-check if all items ID defined manually are correct. The integration [don't support unknown or incorrect item ID - see issue](https://github.com/Chouffy/home_assistant_tgtg/issues/22).
