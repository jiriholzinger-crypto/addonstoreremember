# Paměť řazení v Katalogu doplňků

Doplněk pro NVDA, který umožňuje zvolit, na které kartě se Katalog doplňků otevře, a pamatuje si, jak je seřazen seznam doplňků v Katalogu doplňků.

NVDA zapomene volbu „Seřadit podle sloupce“ při každém otevření Katalogu doplňků i při přepnutí karty.
S tímto doplňkem může být seznam pokaždé seřazen podle data zveřejnění nebo data instalace od nejnovějších,
nebo přesně tak, jak jste ho seřadili naposledy.

## Nastavení

Nabídka NVDA → Možnosti → Nastavení → kategorie „Paměť řazení v Katalogu doplňků“:

* **Spravovat řazení seznamu v Katalogu doplňků** – zapíná nebo vypíná doplněk.
* **Režim řazení**
  * *Pamatovat si naposledy zvolené řazení* – co vyberete v poli „Seřadit podle sloupce“ (nebo kliknutím na záhlaví sloupce), použije se i příště. Dokud nic nevyberete, použije se výchozí řazení níže.
  * *Vždy použít výchozí řazení níže* – výchozí řazení se použije pokaždé, vaše změny platí jen do přepnutí karty nebo zavření katalogu.
* **Pamatovat si řazení zvlášť pro každou kartu** – každá karta má vlastní řazení; když není zaškrtnuto, sdílí se jedno řazení pro všechny karty. Pokud zapamatovaný sloupec na kartě není (Datum instalace u Dostupných doplňků), použije se výchozí řazení karty.
* **Výchozí řazení pro jednotlivé karty** (Nainstalované, K aktualizaci, Dostupné, Nekompatibilní): výchozí NVDA, datum zveřejnění od nejnovějších/nejstarších, datum instalace od nejnovějších/nejstarších (datum instalace jen u karet Nainstalované a Nekompatibilní).
* **Zapomenout zapamatované řazení** – smaže zapamatované volby.
* **Karta, která se otevře při vstupu do Katalogu doplňků** – výchozí NVDA (Nainstalované doplňky, nebo Dostupné, pokud žádné nejsou nainstalovány), naposledy použitá karta, nebo pevně zvolená karta: Nainstalované, K aktualizaci, Dostupné nebo Nekompatibilní doplňky.
* **Použít tuto kartu i tehdy, když NVDA otevře katalog kvůli aktualizacím doplňků** – když NVDA otevře katalog z oznámení o aktualizacích doplňků, jde normálně na kartu K aktualizaci; zaškrtnutím se i tehdy použije vaše zvolená karta.

Výchozí nastavení: režim zapamatování, zvlášť pro každou kartu; Nainstalované a Nekompatibilní podle data instalace od nejnovějších, K aktualizaci a Dostupné podle data zveřejnění od nejnovějších.

Řazení podle „Relevance“ během hledání se nikdy neukládá a po vymazání hledání se vrátí zapamatované řazení.

## Požadavky

NVDA 2025.1 nebo novější (sloupce s datem přibyly do Katalogu doplňků ve verzi 2025.1).

## Licence

Copyright (C) 2026 Jiří Holzinger. GNU General Public License verze 2 nebo novější.
