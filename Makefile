.PHONY: install
PREFIX = /usr

install:
	install -d "${DESTDIR}${PREFIX}/bin"
	install -m 755 reflex_curses/reflex.py "${DESTDIR}${PREFIX}/bin/reflex-curses"
	install -d "${DESTDIR}${PREFIX}/share/man/man1"
	install -m 644 docs/reflex-curses.1 "${DESTDIR}${PREFIX}/share/man/man1/reflex-curses.1"
