## Konto administracyjne

- Użytkownik: `figielak`, UID 1000, GID 1000
- Grupy: sudo, docker (docker dodana przy instalacji Dockera)
- Hasło: menedżer haseł, wpis „Homelab Castle" — służy do sudo
  i logowania lokalnego; logowanie hasłem po SSH wyłączone
- Klucz SSH: <do uzupełnienia w kroku hardeningu>

**UID 1000 jest istotny dla odtworzenia.** Bind mounty w
/srv/homelab/data/ zapisują właściciela numerycznie. Przy odbudowie
na nowym sprzęcie konto administracyjne musi powstać jako pierwsze,
żeby dostać ten sam UID — inaczej przywrócone dane będą miały
niepasującego właściciela i kontenery nie zapiszą.

**Ryzyko przyjęte świadomie:** grupa `docker` daje uprawnienia
równoważne rootowi (dostęp do socketu Dockera pozwala zamontować /
do kontenera). Akceptowane przy jednym administratorze; przy dodaniu
drugiej osoby wymaga ponownej oceny.