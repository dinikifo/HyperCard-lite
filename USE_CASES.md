# HyperCard Lite — Example Use Cases

This file lists small projects you can build to get familiar with the environment.

---

## 1. Contact Collector

**UI:**
- Field: Name = `ContactName`
- Button: `Save`
- Button: `Show all`

**Save**:
```text
on click
  get field "ContactName" into "n"
  sql "CREATE TABLE IF NOT EXISTS contacts(name TEXT)"
  sql "INSERT INTO contacts(name) VALUES('{n}')"
  answer "Saved {n}"
end click
```

**Show all**:
```text
on click
  sql "SELECT name FROM contacts"
end click
```

---

## 2. TODO Pad

**UI:**
- Field: Name = `TodoText`
- Button: `Add`
- Button: `Show todos`

**Add**:
```text
on click
  get field "TodoText" into "t"
  sql "CREATE TABLE IF NOT EXISTS todos(item TEXT)"
  sql "INSERT INTO todos(item) VALUES('{t}')"
  answer "Added"
end click
```

**Show**:
```text
on click
  sql "SELECT item FROM todos"
end click
```

---

## 3. Personal Expense Tracker (simple)

**UI:**
- Field: Name = `Amount`
- Field: Name = `Category`
- Field: Name = `Note`
- Button: `Save expense`
- Button: `Show expenses`

**Save**:
```text
on click
  get field "Amount" into "a"
  get field "Category" into "c"
  get field "Note" into "n"
  sql "CREATE TABLE IF NOT EXISTS expenses(amount TEXT, category TEXT, note TEXT)"
  sql "INSERT INTO expenses(amount, category, note) VALUES('{a}','{c}','{n}')"
  answer "Saved {a}"
end click
```

**Show**:
```text
on click
  sql "SELECT amount, category, note FROM expenses"
end click
```

---

## 4. Vocabulary Notebook

**UI:**
- Field: Name = `Word`
- Field: Name = `Meaning`
- Button: `Add word`
- Button: `Show words`

**Add**:
```text
on click
  get field "Word" into "w"
  get field "Meaning" into "m"
  sql "CREATE TABLE IF NOT EXISTS vocab(word TEXT, meaning TEXT)"
  sql "INSERT INTO vocab(word, meaning) VALUES('{w}','{m}')"
  answer "Added {w}"
end click
```

**Show**:
```text
on click
  sql "SELECT word, meaning FROM vocab"
end click
```

---

## 5. Logger

**UI:**
- Field: Name = `LogText`
- Button: `Log it`
- Button: `Show log`

**Log it**:
```text
on click
  get field "LogText" into "x"
  sql "CREATE TABLE IF NOT EXISTS logs(msg TEXT)"
  sql "INSERT INTO logs(msg) VALUES('{x}')"
  answer "Logged"
end click
```

**Show**:
```text
on click
  sql "SELECT msg FROM logs"
end click
```

---

## 6. Navigation Stack

**Cards:**
- Start
- Details
- Checklist

**Example button**:
```text
on click
  go card "Checklist"
end click
```

---

## License / Public Domain

This document is released into the public domain. You can copy, modify, and redistribute it without restriction.
