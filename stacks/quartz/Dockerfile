# Narzedzie do budowania, nie usluga: generuje statyczny HTML z docs/
# i konczy prace. Gotowa strone serwuje Caddy.
#
# Quartz nie jest paczka npm, tylko projektem do sklonowania — dlatego
# klonujemy go tutaj po tagu, zamiast trzymac ~300 jego plikow w tym repo.
FROM node:22.16.0-slim

ARG QUARTZ_VERSION

# `quartz plugin install` pobiera pluginy przez systemowy `git clone`
# (kazdy plugin v5 to osobne repo, przypiete do commita w quartz.lock.json).
RUN apt-get update \
 && apt-get install -y --no-install-recommends git ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Uzytkownik node z obrazu ma UID 1000 — pliki strony naleza do figielak.
WORKDIR /quartz
RUN chown node:node /quartz
USER node

RUN git clone --depth 1 --branch "${QUARTZ_VERSION}" \
      https://github.com/jackyzha0/quartz.git . \
 && npm ci \
 && npx quartz plugin install

# --directory to katalog z TRESCIA (quartz/cli/args.js), mimo ze strona
# dokumentacji `quartz build` opisuje go jako katalog projektu.
#
# --output wskazuje PODKATALOG montowania, nie sam punkt montowania:
# build kasuje katalog wyjsciowy w calosci (rm -r), a punktu montowania
# skasowac sie nie da.
ENTRYPOINT ["npx", "quartz", "build", "--directory", "/content", "--output", "/out/public"]
