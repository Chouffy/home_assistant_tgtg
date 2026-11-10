# Too Good To Go integration for Home Assistant

This aims to show the stock of one or multiple [Too Good To Go](https://toogoodtogo.com/) items using the [tgtg-python](https://github.com/ahivert/tgtg-python) library.
Sensor data can be used afterward to generate notifications, history graphs, ... share your best examples in the [Discussion tab](https://github.com/Chouffy/home_assistant_tgtg/discussions)!

## Features

- **Easy setup** - No tokens, Docker containers, or Python scripts needed! Just enter your email and enter the PIN from the login email.
- **Config Flow** - Full UI-based configuration
- **Automatic favorites** - Retrieves all your favorites from the TGTG app (with pagination for accounts with 20+ favorites)
- **Smart polling** - More frequent updates (every 3 minutes) during sales windows when items are likely to become available
- **API rate limiting** - Built-in 1 second delays between API calls to prevent rate limiting issues
- **Reauth support** - Handles token expiration gracefully
- **Diagnostics** - Built-in diagnostics support for troubleshooting
- **Custom item IDs** - Optionally add non-favorite items during setup
- **Rich attributes** for each sensor:
  - Item ID and URL
  - Price and original value
  - Pick-up start and end time
  - Sold-out timestamp
  - Store logo and cover image URLs
  - Pickup location (latitude/longitude)
  - Orders placed and quantity ordered
  - Pickup window changed status
  - Cancel-until time

## Installation

### Via [HACS](https://hacs.xyz/) (Recommended)

1. Search for _TooGoodToGo_ in the Integration tab of HACS
2. Click _Install_
3. Restart Home Assistant
4. Go to **Settings** → **Devices & Services** → **Add Integration**
5. Search for "TooGoodToGo" and follow the setup wizard
6. Enter your TGTG email address and submit
  > If additional verification is required, use the CAPTCHA link when provided and wait before retrying. Repeated attempts can prolong a block.
7. Check your email for a PIN code from Too Good To Go (**open it in a new tab**) and enter it in the setup wizard
8. Optionally add any non-favorite item IDs
9. Done!

## Configuration

Configuration is performed entirely in the UI. No YAML configuration is needed.

### Adding custom item IDs

During setup, you can optionally add item IDs for stores that aren't in your favorites. To find an item ID:

1. Open the Too Good To Go app
2. Navigate to the store you want to add
3. Share the store link - it will look like: `https://share.toogoodtogo.com/item/123456/`
4. The number at the end (`123456`) is the item ID

## How polling works

- **Default polling**: Every 60 minutes, configurable in the integration options (1-1440 minutes)
- **Sales window polling**: Every 3 minutes during the first 10 minutes of a sales window, configurable in the integration options (0-1440 minutes; 0 disables faster polling)
- **Jitter**: Each next polling interval includes an independent random variation of up to 30 seconds in either direction
- **Rate limited**: 1 second delay between API calls to prevent being blocked
- **Adaptive**: HTTP 403/429 pauses requests for one hour, including after a Home Assistant restart. Jitter does not shorten this pause.

Open the integration's options to change intervals without renewing authentication.
For example, set the normal interval to 120 and the sales-window interval to 0
to poll roughly every two hours without a faster sales-window mode. Saving options
reloads only this integration. One update may make multiple API calls for favorites,
additional items and orders; a longer interval does not guarantee avoiding a CAPTCHA.

Additional item IDs returning HTTP 410 are remembered and skipped on subsequent
requests without removing them from your configuration. An item reappearing in
favorites is automatically restored to individual polling.

> **Note**: Each time you add/remove a favorite in the TGTG app, **reload the integration** for changes to take effect.

## Automation example

Here's an example automation that sends a notification when a TGTG item becomes available:

```yaml
automation:
  - alias: "TGTG Item Available"
    trigger:
      - platform: state
        entity_id: sensor.tgtg_your_store_name
    condition:
      - condition: template
        value_template: "{{ trigger.to_state.state | int > 0 }}"
    action:
      - service: notify.mobile_app_your_phone
        data:
          title: "TGTG Surprise Bag Available!"
          message: >
            {{ trigger.to_state.attributes.friendly_name }} has {{ trigger.to_state.state }} bag(s) available!
            Pickup: {{ trigger.to_state.attributes.pickup_start | as_datetime | as_local }}
            Price: {{ trigger.to_state.attributes.item_price }}
          data:
            url: "{{ trigger.to_state.attributes.item_url }}"
```

> **Note**: All attributes use snake_case (underscores), e.g., `pickup_start`, `item_price`, `item_url`.

## Dashboard card example

Here is an example for a card on your Home Assistant dashboard created by @wallieboy, updated by @Sarnog in https://github.com/Chouffy/home_assistant_tgtg/issues/73 and @tjorim. Support for images was later added by @ov3rk1ll in https://github.com/Chouffy/home_assistant_tgtg/pull/139.
Make sure you install the custom `auto-entities` and `multiple-entity-row` cards as well.

```yaml
type: custom:auto-entities
card:
  type: entities
  title: TGTG Surprise Bags
filter:
  template: |-
    {% for state in states.sensor if state.entity_id in integration_entities('tgtg') %}
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

## Troubleshooting

### "Additional verification required" during setup

Too Good To Go may require a DataDome CAPTCHA. When the API supplies a valid
HTTPS challenge URL on `captcha-delivery.com`, the integration shows the complete
link in a persistent notification and the setup error form. Open it manually on
the same network as Home Assistant. Links may expire, and verification in a browser
may not unlock the integration's session because of IP or cookie binding. Do not
share challenge URLs. The integration does not solve or bypass CAPTCHAs.

Related to [issue #204](https://github.com/Chouffy/home_assistant_tgtg/issues/204),
the client uses an explicit updated Android User-Agent instead of the library's
old defaults. It is passed through the supported `TgtgClient` constructor argument,
not patched in `site-packages`. This workaround is not guaranteed to prevent blocks.

### Integration stops updating

HTTP 401 requests reauthentication. Use **Reconfigure** on the existing integration
to renew the session manually; a new PIN email is requested only after confirmation.
Your configured items and entity IDs are retained, and renewed tokens are persisted.
Do not delete the integration to renew credentials. A setup-retry message after a
403/429 includes the pause deadline; it does not mean a new login is being attempted.

### Not all favorites showing

If you have more than 20 favorites, make sure you're using version 6.0.0 or later which includes pagination support.

### Enable debug logging

Add this to your `configuration.yaml` and restart Home Assistant:

```yaml
logger:
  default: info
  logs:
    custom_components.tgtg: debug
```

## Breaking changes in v6.0.0

- **Config flow only**: YAML configuration is deprecated. Existing YAML configs will be automatically migrated to UI-based configuration on first load. You can then remove the YAML config from your configuration.yaml.
