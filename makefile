CC=gcc
CFLAGSOPT=-O3 -W -Wall -Wextra -Wunused -DNDEBUG
CFLAGSDEF=-W -Wall -Wextra -Wunused -g

all: opt

opt: certcheck.c simpleaig.c certcheck_version.h
	${CC} ${CFLAGSOPT} -c simpleaig.c -o simpleaig.o
	${CC} ${CFLAGSOPT} certcheck.c -o certcheck simpleaig.o

debug: certcheck.c simpleaig.c certcheck_version.h
	${CC} ${CFLAGSDEF} -c simpleaig.c -o simpleaig.o
	${CC} ${CFLAGSDEF} certcheck.c -o certcheck simpleaig.o

clean:
	rm -f *.o
	rm -f certcheck

.PHONY: all clean 
