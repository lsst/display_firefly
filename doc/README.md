Sphinx documentation support is still be developed. For now, install dependencies listed in `requirements.txt`.

To make the docs for `display_firefly` alone:

```
setup display_firefly
sphinx-build -b html -n -d _build/doctrees  . _build/html
```

