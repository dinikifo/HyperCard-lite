# HyperCard Lite — User Manual

This manual describes the current prototype UI and scripting model.

---

## 1. Layout

When you run the app you get:

- **Center**: the current card (HTML)
- **Left dock — “Cards”**: list of cards in the stack
- **Right dock — “Properties”**: edit selected part
- **Bottom dock — “Data Output”**: shows SQL results / errors
- **Menu bar**:
  - **Mode** → Browse / Edit
  - **Card** → new / delete / edit card script
  - **Insert** → button / field

---

## 2. Modes

### Browse mode
- Clicks **run** scripts.
- Fields (if unlocked) can be typed into.
- Use to **try** the stack.

### Edit mode
- Clicks **select** parts.
- Selected part appears in Properties.
- Parts get dashed outline.
- Parts can be **dragged** to new positions.
- Use to **design** the stack.

Switch with **Mode → Browse** or **Mode → Edit**.

---

## 3. Cards

- Start with 2 cards.
- **Card → New card**: adds a card.
- **Card → Delete current card**: removes current card (not the last).
- **Card → Edit card script…**: write a script that runs on that card, e.g.:

  ```text
  on openCard
    answer "Welcome"
  end openCard
  ```

- Click a card in the left dock to go to it.

---

## 4. Parts (buttons and fields)

Add parts with **Insert**:

- **Insert → Button**
- **Insert → Field**

Then:

1. Switch to **Edit**
2. Click the part → it shows in Properties
3. Drag it to reposition
4. Change text / name / script
5. Click **Apply**

**Properties you can edit:**

- **Name** (used in scripts)
- **X, Y** (position)
- **Width, Height**
- **Text** (label / field contents)
- **Lock text** (for fields)
- **Script** (per-part script)
- **Apply** (save to DB)

---

## 5. Scripting

Scripts are written as events:

```text
on click
  ...commands...
end click
```

or

```text
on openCard
  ...commands...
end openCard
```

### Available commands

**Navigation**
```text
go next card
go prev card
go card "Card 2"
go card 3
```

**Message**
```text
answer "Hello!"
answer "Saved {name}"
```

(Variables in `{}` are replaced with the values captured earlier in the script run.)

**Write to field**
```text
set field "Notes" to "Updated"
```

**Read from field**
```text
get field "CustomerName" into "n"
```
This looks up the field on the current card whose **Name** is `CustomerName` and stores its current text into the script variable `n`.

**SQL (user DB only)**
```text
sql "CREATE TABLE IF NOT EXISTS customers(name TEXT)"
sql "INSERT INTO customers(name) VALUES('Alice')"
sql "SELECT name FROM customers"
sql "SELECT name FROM customers" into "first"
```

- Without `into`, results are shown in the **Data Output** dock.
- With `into`, the first column of the first row is stored in that variable.

**Combining field + SQL + answer**
```text
on click
  get field "CustomerName" into "n"
  sql "CREATE TABLE IF NOT EXISTS customers(name TEXT)"
  sql "INSERT INTO customers(name) VALUES('{n}')"
  answer "Saved {n}"
end click
```

---

## 6. Data Output dock

- Shows the result of `sql "SELECT ..."` commands
- Shows SQL errors
- Non-modal; you can leave it open while clicking buttons

---

## 7. Data model

- Runtime stack (cards, parts, scripts) lives in an internal SQLite DB
- User data (your tables like `customers`, `todos`, `notes`) lives in `user_data.db`
- Scripts only run SQL on the **user** DB to avoid breaking the stack

---

## 8. Tips

- Scripts match fields by **Name**, not Text
- Always test in **Browse** mode
- Keep scripts one command per line
- If nothing happens: check you’re not in Edit
- Use bottom dock to debug SQL

---

## License / Public Domain

This document is released into the public domain. You can copy, modify, and redistribute it without restriction.
