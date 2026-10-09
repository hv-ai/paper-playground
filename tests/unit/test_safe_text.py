from ui.safe_text import md_safe


def test_links_html_and_math_are_neutralised():
    out = md_safe("[click](http://evil.example) <script>x</script> $$1+1$$ ![img](x)")
    for token in ("[", "]", "(", ")", "<", ">", "$", "!"):
        assert "\\" + token in out
        assert out.replace("\\" + token, "").count(token) == 0
