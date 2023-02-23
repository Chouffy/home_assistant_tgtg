# TooGoodToGo items stock as a sensor in Home Assistant

This aim to show the stock of one or multiple [TooGoodToGo](https://toogoodtogo.com/) item using the [tgtg-python](https://github.com/ahivert/tgtg-python) library.  
Sensor data can be used afterward to generate notifications, history graphs, ... share your best examples in the [Discussion tab](https://github.com/Chouffy/home_assistant_tgtg/discussions)!

## Usage

### Installation via [HACS](https://hacs.xyz/)

1. Search for *TooGoodToGo* in the Integration tab of HACS
1. Click *Install*
1. Restart the Home Assistant server
1. Go to *Configuration* -> *Devices & Services* and setup a new TGTG integration using your email 

## Features

* No Docker-Container needed!!!
* No local Python-Scripts and knowledge needed!!!
* Fetch each item stock defined
* ConfigFlow for easy configuration
* Retrieve all favorites
* Retrieve additional information as attributes, if available:
    * Item ID
    * Store ID
    * TooGoodToGo price and original value
    * Pick-up start and end
    * Sold-out date
    * Sales Window
    * Store Logo URL

## How is it polling the data

- This integration is polling all favourites every 15 minutes.
- Every 2 hours the details of an item (for every item in favourites list) are fetched to update the saleswindow and/or pickup dates and other data of the item
- If an item is inside his saleswindow (from start of saleswindow till 10 minutes later) it will be fetched more frequently (every 3 minutes)

