# mKraków dla Home Assistanta

Nieoficjalna integracja z aplikacją **mKraków**: czyta Twoje bilety okresowe KKM (Karta Krakowiaka)
i pokazuje, do kiedy jest ważny bilet. Korzysta z tego samego API co aplikacja (`api.um.krakow.pl`).

> Projekt prywatny, niezwiązany z Urzędem Miasta Krakowa. API nie jest publiczne i może się zmienić.

## Jak działa logowanie

mKraków wymaga kodu SMS przy każdym logowaniu. Integracja loguje się **raz** (PESEL, numer telefonu, kod SMS),
a potem co 30 minut odświeża sesję tokenem odświeżania (refresh token), więc kolejne SMS-y nie są potrzebne,
dopóki serwer nie zerwie sesji.

Gdy sesja wygaśnie, HA pokaże „Reconfigure” przy integracji (klikasz Wyślij i wpisujesz nowy kod SMS),
a na szynie pojawi się zdarzenie `mkrakow_sesja_wygasla` – możesz z niego zrobić powiadomienie.

## Instalacja (HACS)

1. HACS → ⋮ → **Custom repositories** → `https://github.com/Dadzzio/mkrakow-ha`, kategoria **Integration**.
2. Znajdź **mKraków** → **Download** → restart HA.
3. **Settings → Devices & services → Add integration → mKraków**.

### Stałe aplikacji (3 pola)

W repo nie ma kluczy aplikacji mKraków. Skopiuj je z nagrania ruchu aplikacji (np. Proxyman na iPhonie),
z dowolnego zapytania do `api.um.krakow.pl`:

| Pole | Skąd |
|---|---|
| Nagłówek apikey | nagłówek `apikey` z dowolnego zapytania |
| Authorization z /mkrakow-sms/login | nagłówek `Authorization` zapytania `POST /mkrakow-sms/login` (zaczyna się od `Basic`) |
| Authorization z /mkrakow-oauth/token | nagłówek `Authorization` zapytania `POST /mkrakow-oauth/token` albo `/mkrakow-oauth/revoke` (`Basic`) |

Najprościej: zapisz nagranie jako `.har` i uruchom na komputerze
`python3 narzedzia/stale_z_har.py nagranie.har` – skrypt wypisze tylko te trzy wartości
(bez PESEL-u, numeru telefonu i tokenów). Możesz podać kilka plików naraz.

Nie wysyłaj nikomu całego nagrania – są w nim PESEL, numer telefonu i tokeny.

## Encje (urządzenie „mKraków”)

| Encja | Stan | Atrybuty |
|---|---|---|
| `sensor.mkrakow_waznosc_biletu` | data i godzina końca ważności (timestamp) | `bilet` (nazwa, od, do, status, cena), `aktualny`, `bilety` |
| `sensor.mkrakow_dni_do_konca` | liczba dni do końca | – |
| `sensor.mkrakow_sesja` | kiedy zalogowano kodem SMS (diagnostyczna) | `ostatnia_aktualizacja` |

Jeśli masz kupiony kolejny bilet zaczynający się później, ważność to koniec **ostatniego** biletu.
Bilety zwrócone i przeterminowane są pomijane.

## Przykład: przepisanie daty do helpera

```yaml
triggers:
  - trigger: state
    entity_id: sensor.mkrakow_waznosc_biletu
conditions:
  - condition: template
    value_template: "{{ states('sensor.mkrakow_waznosc_biletu') not in ['unknown', 'unavailable'] }}"
actions:
  - action: input_datetime.set_datetime
    target:
      entity_id: input_datetime.waznosc_biletu_kkm
    data:
      timestamp: "{{ as_timestamp(states('sensor.mkrakow_waznosc_biletu')) }}"
```
