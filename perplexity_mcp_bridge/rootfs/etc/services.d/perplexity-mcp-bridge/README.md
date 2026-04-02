# Obs

Själva filen `run` **kopieras inte** in i imagen längre. Den genereras i **Dockerfile** med `echo` (alltid LF, inga CRLF från Windows/Git).

Om du ändrar startkommandot: uppdatera motsvarande `RUN install -d ... && { echo ... }` i `Dockerfile`.
