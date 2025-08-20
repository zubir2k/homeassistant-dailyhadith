![image](https://github.com/user-attachments/assets/f6d5f329-07a5-460b-82e2-6ded4a6b9012)

![GitHub Repo stars](https://img.shields.io/github/stars/zubir2k/homeassistant-dailyhadith?style=social)
[![hacs_badge](https://img.shields.io/badge/HACS-Default-41BDF5.svg)](https://github.com/hacs/default)
[![hacs_badge](https://img.shields.io/badge/HACS-Integration-41BDF5.svg)](https://github.com/hacs/integration)
![GitHub all releases](https://img.shields.io/badge/dynamic/json?color=41BDF5&logo=home-assistant&label=Download%20Count&suffix=%20installs&cacheSeconds=15600&url=https://analytics.home-assistant.io/custom_integrations.json&query=$.daily_hadith.total)
[![Buy](https://img.shields.io/badge/Support-Sunnah.com-darkgreen.svg)](https://sunnah.com/donate)
[![GitHub Release](https://img.shields.io/github/release/zubir2k/homeassistant-dailyhadith.svg)](https://github.com/zubir2k/homeassistant-dailyhadith/releases/)

Assalamu'alaikum

This is a custom integration on Daily Hadith from Sunnah.com for your Home Assistant 🏠 \
_May this benefit you, inshaAllah._

## 🛠️ What's New: Fallback Hadith Source Updated

- For users **without an API key**, daily hadith content is now updated independently.
- No action required—fallback data is always up to date!

## 🚩 Features
- Daily random hadith which will refresh midnight.
- Information includes hadith in `arabic` and `english`
- Full references from chapters, collection names, etc.

![image](https://github.com/user-attachments/assets/9b292af6-7b90-48ba-8db7-ceda1d790d85)

## 🎯 Use Cases
- Display daily hadith on your Home Assistant dashboard
- Automate daily hadith via notifications, or instant messaging (e.g. Family Group)

![wasap](https://github.com/user-attachments/assets/72477c1c-a3b4-469a-b732-a7b2d94f3b10)

## 🕹️ Installation
#### With HACS
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=zubir2k&repository=homeassistant-dailyhadith&category=integration)

> [!Tip]
> If you are unable to use the button above, manually search for Daily Hadith in HACS.

#### Manual
1. Copy the `daily_hadith` directory from `custom_components` in this repository and place inside your Home Assistant's `custom_components` directory.
2. Restart Home Assistant
3. Follow the instructions in the `Setup` section

> [!WARNING]
> If installing manually, in order to be alerted about new releases, you will need to subscribe to releases from this repository.

## 📦 Setup
[![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=daily_hadith)

> [!Tip]
> If you are unable to use the button above, follow the steps below:
> 1. Navigate to the Home Assistant Integrations page (Settings --> Devices & Services)
> 2. Click the `+ ADD INTEGRATION` button in the lower right-hand corner
> 3. Search for `Daily Hadith`
> 4. Enter your API key from Sunnah.com. Leave empty if you have no API key and press Submit.
> 
> Create an `Issue` at Sunnah.com Github Repository to request for the API key [here](https://github.com/sunnah-com/api/issues/new?template=request-for-api-access.md&title=Request+for+API+access%3A+%5BYour+Name%5D)

## 🪄 Markdown Card
You may use below template for your markdown card.

![image](https://github.com/user-attachments/assets/2d725f01-8718-46d8-bf79-043b1dbbbfec)

```yaml
type: markdown
content: |-
  ### {{ state_attr("sensor.daily_hadith", "title") }}

  {{ state_attr("sensor.daily_hadith", "arabic") }}

  {{ state_attr("sensor.daily_hadith", "text") }}
title: 📿 Daily Hadith
```

## 🎖️ Credits
Data provided by Sunnah.com. Learn [more](https://sunnah.com/about) about Sunnah.com

## 📢 Join the Community
[Home Assistant Official Community](https://community.home-assistant.io/t/custom-integrations-daily-hadith/) \
[Home Assistant Malaysia](https://www.facebook.com/groups/homeassistantmalaysia)
