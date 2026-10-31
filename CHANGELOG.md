# Changelog

## 0.2.0
- **New periods**: New Year's Eve 🎆 (Dec 31 – Jan 1, small fireworks at the top of the screen) and Valentine's Day 💘 (Feb 12–14, falling hearts). Short periods use `"senza_pausa": true`: they interrupt the current period without "normal" buffer days.
- **Personal days** (Configure → Personal days): birthdays and anniversaries, one per line `MM-DD Name emoji #color`. Confetti and your color on that day.
- **Calendar entity** `calendar.seasonal_glass`: every period of the year in the HA Calendar panel and usable in calendar triggers.
- **Sensor attributes**: `fine`, `prossimo`, `prossimo_id`, `prossimo_icona`, `prossimo_inizio`, `giorni_al_prossimo`.
- **Service `seasonal_glass.anteprima`**: show a period on every device for N minutes (0 = cancel).
- Animations now **follow the device's "reduce motion" setting by default** (Configure → General → Animations to change it).
- Animations also pause when the page is hidden.
- New periods start enabled even if you had already picked the active periods (only what you switched off stays off).
- Fix: Feb 29 dates in non-leap years now fall on Feb 28 in the frontend too (same as the sensor).
- Test that the JS and Python calendars match day by day (runs in GitHub Actions).

## 0.1.4
- Sensor `sensor.seasonal_glass_periodo` with an HA notification when the decoration changes.
- Halloween: half-moon cobweb on the right; Christmas: baubles on the sides.

## 0.1.3 and earlier
- First public releases: 8 periods, light/dark, Configure menu (general, dates, colors), calendar card, kiosk support.
