# Scenario: weather-simple

Exercises the full pipeline (intake → docs, including the eval loop) with no
credentials: Open-Meteo needs no API key.

## Prompt

/weni:new-agent Build a "weather-advisor" collaborator for WhatsApp. When the contact asks
about the weather in a city, it looks up the current weather with the free Open-Meteo
APIs (geocoding to resolve the city, then the forecast endpoint) and recommends what
to wear. It does not use VTEX or Retail Setup. It answers in English.

## Watch for

- Readiness gate blocks correctly if you are logged out.
- Eval criteria are about facts (city, weather, coherent clothing), not wording.
- Triage table classifies failures sensibly; loop ends within 3 rounds.
