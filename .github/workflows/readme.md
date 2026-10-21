# Add-on Store Sort Memory

An NVDA add-on that lets you choose which tab the Add-on Store opens on, and remembers how the add-on list in the Add-on Store is sorted.

NVDA forgets the "Sort by column" choice every time the Add-on Store is opened or you switch tabs.
With this add-on, the list can be sorted by publication date or install date, newest first,
every time — or exactly the way you sorted it last time.

## Settings

NVDA menu → Preferences → Settings → category "Add-on Store Sort Memory":

* **Manage sorting of the Add-on Store list** – turns the add-on on or off.
* **Sorting mode**
  * *Remember the last sort I chose* – whatever you pick in "Sort by column" (or by clicking a column header) is used again next time. Until you choose something, the default sort below is used.
  * *Always use the default sort below* – the default sort is applied every time, your changes last only until the tab is switched or the store is closed.
* **Remember sorting separately for each tab** – each tab keeps its own sort; if unchecked, one sort is shared by all tabs. If the remembered column does not exist on a tab (Install date on Available add-ons), the tab's default sort is used.
* **Default sort for each tab** (Installed, Updatable, Available, Incompatible add-ons): NVDA default, publication date newest/oldest first, install date newest/oldest first (install date only on the Installed and Incompatible tabs).
* **Forget remembered sorting** – clears the remembered choices.
* **Tab to open when entering the Add-on Store** – NVDA default (Installed add-ons, or Available if none are installed), the last used tab, or a fixed tab: Installed, Updatable, Available or Incompatible add-ons.
* **Use this tab also when NVDA opens the store to show add-on updates** – normally, when NVDA opens the store from its add-on update notification, it goes to Updatable add-ons; check this to use your chosen tab even then.

Defaults: remember mode, per tab; Installed and Incompatible by install date newest first, Updatable and Available by publication date newest first.

Sorting by "Relevance" while searching is never remembered, and clearing the search returns to the remembered sort.

## Requirements

NVDA 2025.1 or later (the date columns were added to the Add-on Store in 2025.1).

## License

Copyright (C) 2026 Jiří Holzinger. GNU General Public License version 2 or later.
