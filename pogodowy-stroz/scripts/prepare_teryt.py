# scripts/prepare_teryt.py
import pandas as pd
import json
import unicodedata
import os
from pathlib import Path

# Konfiguracja ścieżek
BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA_DIR = BASE_DIR / "raw_data"
DATA_DIR = BASE_DIR / "app" / "data"

# Nazwy plików wejściowych (pobrane ze strony GUS TERYT)
TERC_FILENAME = "TERC.csv"  # Nazwa przykładowa, dostosuj do posiadanego pliku
SIMC_FILENAME = "SIMC.csv"  # Nazwa przykładowa, dostosuj do posiadanego pliku


def normalize_text(text: str) -> str:
    """
    Normalizuje tekst: zamienia na małe litery, usuwa polskie znaki diakrytyczne.
    Np. "Gdańsk" -> "gdansk", "Łódź" -> "lodz".
    Jest to kluczowe dla dopasowywania zapytań użytkownika[cite: 65].
    """
    if not isinstance(text, str):
        return ""
    text = text.lower()
    # Dekompozycja znaków (np. ą = a + ogonek) i usunięcie znaków łączących (ogonek)
    text = "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")
    return text.strip()


def prepare_terc():
    """Przetwarza plik TERC (powiaty)[cite: 36, 48]."""
    print(f"Przetwarzanie {TERC_FILENAME}...")
    file_path = RAW_DATA_DIR / TERC_FILENAME

    if not file_path.exists():
        print(f"BŁĄD: Nie znaleziono pliku {file_path}. Pobierz go z eteryt.stat.gov.pl.")
        return {}

    # Wczytanie CSV (GUS używa średnika jako separatora)
    df = pd.read_csv(file_path, sep=';', dtype=str, encoding='utf-8')

    terc_dict = {}

    # Filtrujemy tylko powiaty (nie województwa i nie gminy)
    # W bazie TERYT powiaty mają wypełnione WOJ i POW, a GMI jest puste (lub specyficzne oznaczenie RODZ)
    # Dla uproszczenia szukamy jednostek z frazą "powiat" lub "miasto na prawach powiatu" w NAZWA_DOD

    # Kolumny w TERC: WOJ;POW;GMI;RODZ;NAZWA;NAZWA_DOD;STAN_NA
    for _, row in df.iterrows():
        nazwa_dod = str(row.get('NAZWA_DOD', '')).lower()

        if 'powiat' in nazwa_dod:
            woj = row['WOJ']
            powiat = row['POW']
            nazwa = row['NAZWA']

            # Tworzymy pełny kod TERYT powiatu (zazwyczaj 4 cyfry: WWPP)
            teryt_code = f"{woj}{powiat}"

            # Normalizacja klucza
            key = normalize_text(nazwa)  # np. "poznanski"

            # Dodajemy też wariant z prefiksem "powiat", o który może zapytać użytkownik [cite: 49]
            key_full = normalize_text(f"powiat {nazwa}")

            terc_dict[key] = teryt_code
            terc_dict[key_full] = teryt_code

    return terc_dict


def prepare_simc():
    """Przetwarza plik SIMC (miejscowości)[cite: 39, 48]."""
    print(f"Przetwarzanie {SIMC_FILENAME}...")
    file_path = RAW_DATA_DIR / SIMC_FILENAME

    if not file_path.exists():
        print(f"BŁĄD: Nie znaleziono pliku {file_path}.")
        return {}

    # Wczytanie CSV
    df = pd.read_csv(file_path, sep=';', dtype=str, encoding='utf-8')

    simc_dict = {}

    # Kolumny w SIMC: WOJ;POW;GMI;RODZ_GMI;RM;MZ;NAZWA;SYM;SYMPOD;STAN_NA
    for _, row in df.iterrows():
        nazwa = row['NAZWA']
        sym = row['SYM']  # Unikalny identyfikator miejscowości

        norm_nazwa = normalize_text(nazwa)

        # Uwaga: Miejscowości o tych samych nazwach jest wiele.
        # W prostym prototypie nadpisujemy (ostatnia wygrywa),
        # w wersji produkcyjnej należałoby obsłużyć ujednoznacznienie (np. pytając o powiat).
        simc_dict[norm_nazwa] = sym

    return simc_dict


def main():
    # Upewnij się, że katalog wyjściowy istnieje
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Przetwórz TERC
    terc_data = prepare_terc()
    if terc_data:
        out_path = DATA_DIR / "terc_dict.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(terc_data, f, ensure_ascii=False, indent=2)
        print(f"Zapisano {len(terc_data)} powiatów do {out_path}[cite: 49].")

    # 2. Przetwórz SIMC
    simc_data = prepare_simc()
    if simc_data:
        out_path = DATA_DIR / "simc_dict.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(simc_data, f, ensure_ascii=False, indent=2)
        print(f"Zapisano {len(simc_data)} miejscowości do {out_path}[cite: 49].")


if __name__ == "__main__":
    main()