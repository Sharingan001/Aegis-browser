"""
Aegis Public Suffix List (PSL) support.

registrable_domain("a.b.example.co.uk") -> "example.co.uk"

Usage:
    from aegis_psl import PublicSuffixList
    psl = PublicSuffixList.from_file("public_suffix_list.dat")   # official list, text format
    psl.registrable_domain("login.paypal.com")

Get the official list (text format) from https://publicsuffix.org/list/ and refresh it
regularly. If no file is supplied, a SMALL FALLBACK subset is used so tests run offline;
the fallback is NOT complete and must not be shipped.

Algorithm follows the PSL rules: the longest matching rule wins, "*." wildcard rules
match any one label, "!" exception rules override wildcards, and the default rule is "*".
"""
from __future__ import annotations

FALLBACK_RULES = """
com
net
org
edu
gov
io
dev
app
xyz
example
test
uk
co.uk
org.uk
ac.uk
in
co.in
ac.in
gov.in
au
com.au
jp
co.jp
br
com.br
github.io
blogspot.com
*.ck
!www.ck
""".split()


class PublicSuffixList:
    def __init__(self, rules):
        self.exact, self.wild, self.exc = set(), set(), set()
        for r in rules:
            r = r.strip().lower()
            if not r or r.startswith("//"):
                continue
            if r.startswith("!"):
                self.exc.add(r[1:])
            elif r.startswith("*."):
                self.wild.add(r[2:])
            else:
                self.exact.add(r)

    @classmethod
    def from_file(cls, path: str) -> "PublicSuffixList":
        with open(path, encoding="utf-8") as fh:
            lines = [ln.split()[0] for ln in fh if ln.strip() and not ln.startswith("//")]
        return cls(lines)

    @classmethod
    def fallback(cls) -> "PublicSuffixList":
        return cls(FALLBACK_RULES)

    def public_suffix(self, host: str) -> str:
        labels = host.lower().strip(".").split(".")
        for i in range(len(labels)):                      # exception rules always win
            if ".".join(labels[i:]) in self.exc:
                return ".".join(labels[i + 1:])          # suffix is one label shorter than the rule
        best = 1  # default rule "*": the last label is a suffix
        for i in range(len(labels)):
            cand = ".".join(labels[i:])
            n = len(labels) - i
            if cand in self.exact:
                best = max(best, n)
            parent = ".".join(labels[i + 1:])
            if parent and parent in self.wild:
                best = max(best, n)
        return ".".join(labels[-best:])

    def registrable_domain(self, host: str) -> str:
        host = host.lower().strip(".")
        suffix = self.public_suffix(host)
        labels, slabels = host.split("."), suffix.split(".")
        if len(labels) <= len(slabels):
            return host                                   # host is itself a public suffix
        return ".".join(labels[-(len(slabels) + 1):])


DEFAULT = PublicSuffixList.fallback()


def registrable_domain(host: str) -> str:
    return DEFAULT.registrable_domain(host)
