# Ricordi per Annibale — come si guarda

Questa cartella contiene una presentazione a schermo intero con tutti i
messaggi, le foto e i video raccolti da Facebook e Instagram.

**La presentazione è online qui:** https://tezzutezzu.github.io/annibale-memorial/

Se invece hai la cartella sul computer, si apre come spiegato sotto.

---

## 1. Aprire la presentazione

La presentazione ha bisogno di un piccolo "server" per funzionare: si fa con due
comandi da copiare e incollare. 

1. Apri **Terminale** (si trova in *Applicazioni → Utility → Terminale*).
2. Scrivi `cd ` (con uno spazio dopo) e poi **trascina la cartella dentro la
   finestra del Terminale**: il percorso si scrive da solo. Premi <kbd>Invio</kbd>.
3. Copia e incolla questa riga, poi premi <kbd>Invio</kbd>:

   ```
   python3 -m http.server 8899
   ```

   Comparirà una scritta tipo `Serving HTTP on ...`. Va bene: lascia la finestra
   aperta.
4. Apri il browser e vai a questo indirizzo:

   **http://localhost:8899/**

La presentazione è partita. Quando hai finito, torna nel Terminale e premi
<kbd>Ctrl</kbd>+<kbd>C</kbd> per chiuderla.

> Se il Mac chiede di installare gli "strumenti da riga di comando", accetta e
> riprova: è una cosa normale, serve solo a far funzionare il comando qui sopra.

## 2. Come si usa

| tasto | cosa fa |
| --- | --- |
| <kbd>→</kbd> o <kbd>Spazio</kbd> | ricordo successivo |
| <kbd>←</kbd> | ricordo precedente |
| <kbd>Home</kbd> | torna al primo |
| <kbd>End</kbd> | vai all'ultimo |
| <kbd>⌘</kbd>+<kbd>K</kbd> | cerca un ricordo |

- I messaggi lunghi si scorrono con la rotella del mouse, dentro la loro colonna:
  la pagina intera non si muove mai.
- Se un ricordo non ha foto o video disponibili, il testo occupa tutto lo spazio.
- In alto a destra c'è il conteggio, ad esempio `12 / 248`.

### Foto e video di un ricordo

Se un ricordo contiene più foto o video, sotto l'immagine compaiono due frecce e il
conteggio **Foto 1 / 3** oppure **Video 2 / 3**. Le frecce scorrono tutti i contenuti di quel ricordo;
quelle in fondo alla pagina continuano a cambiare ricordo.

Su smartphone e tablet puoi anche **scorrere il dito sulla foto**: verso sinistra
per la foto successiva, verso destra per la precedente. Il testo continua a
scorrere verticalmente nella propria area.

Puoi usare anche la tastiera: premi <kbd>Tab</kbd> per raggiungere le frecce
delle foto, poi <kbd>←</kbd> e <kbd>→</kbd> per sfogliarle. Fuori da questi
comandi, le frecce della tastiera continuano a cambiare ricordo.
Ogni volta che passi a un altro ricordo, viene mostrato il suo primo contenuto.
Con un solo contenuto, i comandi della galleria non compaiono.

I video si avviano con il pulsante Play del lettore. Cambiando contenuto o
ricordo, la riproduzione si ferma. Quando il lettore ha il fuoco, Spazio e le
frecce controllano il video. I due filmati nei caroselli di Pelizzaro e Fusacchia
sono disponibili nel formato scaricato senza traccia audio.

Quando lo stesso ricordo è stato pubblicato su Facebook e Instagram compare una
sola volta, con il testo più completo e le foto e i video di entrambe le fonti.
Sotto l'autore trovi i collegamenti alle pubblicazioni originali. I collegamenti
già condivisi continuano ad aprire lo stesso ricordo anche dopo una fusione.

### Cercare un ricordo

In alto a destra c'è la casella **Cerca**: basta scrivere una parola o un nome.
Si può cercare sia nel testo del messaggio sia nel nome di chi l'ha scritto, e
non serve scrivere tutto: `bollenti spiriti`, `pisasale`, `cosi` (trova anche
"così") funzionano. Sotto la casella compare un elenco con le frasi trovate:
cliccane una (o premi <kbd>↓</kbd> e <kbd>Invio</kbd>) e la presentazione salta a
quel ricordo.

### Mandare a qualcuno un ricordo preciso

Ogni ricordo ha il suo indirizzo. Guarda la barra degli indirizzi: è qualcosa
tipo

```
https://tezzutezzu.github.io/annibale-memorial/#fb_122107332044579405
```

L'indirizzo cambia da solo mentre scorri, quindi basta copiarlo per condividere
il ricordo che hai davanti. In alternativa clicca l'icona a forma di catena
accanto alla data: copia il link e compare la scritta *Link copiato*.

Chi apre quel link arriva direttamente a quel ricordo, e ricaricando la pagina
resta lì.

### I video

In alto a sinistra, sotto la scritta *PER ANNIBALE*, ci sono due pulsanti:
**Ricordi** (la presentazione) e **Video**. La pagina dei video raccoglie gli
interventi pubblici di Annibale, divisi per periodo (Puglia / Bollenti Spiriti,
Milano / Comune di Milano) e in ordine cronologico.

- Si clicca sull'immagine di un video e il video parte lì, dentro la pagina.
- Le immagini sono solo un'anteprima: i video veri si caricano solo quando li
  fai partire, così la pagina resta leggera.
- L'icona in alto a destra di ogni scheda apre lo stesso video su YouTube.
- Serve la connessione a internet: i video stanno su YouTube.

## 3. Cosa c'è nella cartella

```
index.html                ← la presentazione (è questa che si apre)
video.html                ← la pagina dei video
data/posts.jsonl          ← i testi dei messaggi
data/media/               ← tutte le foto (una cartella per ricordo)
data/posts.csv            ← la stessa roba in forma di foglio di calcolo
```

La cartella si può copiare dove vuoi (anche su una chiavetta), ma
`index.html` deve restare dentro la cartella insieme a `data/`:
se lo sposti da solo, le foto non si trovano più.

Le altre cose (`console/`, `import_console_dump.py`, `fbstore.py`,
`requirements.txt`) servono solo se un giorno si vogliono raccogliere altri
ricordi da Facebook. Per guardare la presentazione non servono.

## 4. Se qualcosa non funziona

**La pagina è bianca o dice "Impossibile caricare data/posts.jsonl".**
Vuol dire che è stata aperta con un doppio clic sull'HTML invece che dal server.
Rifai il punto 1 e usa l'indirizzo `http://localhost:8899/...`.

**Nel Terminale c'è scritto `command not found: python3`.**
Manca Python. Apri il Terminale e scrivi `python3 --version`: se il Mac propone di
installare gli strumenti da riga di comando, accetta e riprova.

**La porta 8899 è già occupata.**
Vuol dire che il server è già acceso: apri direttamente l'indirizzo nel browser.
Se non funziona lo stesso, usa un altro numero, ad esempio
`python3 -m http.server 8900`, e cambia il numero anche nell'indirizzo.

**Alcune foto non si vedono.**
Le foto sono state salvate in `data/media/`. Se il file manca, quella foto non è
mai stata scaricata e ormai il collegamento a Facebook è scaduto: si può
recuperare solo rifacendo la raccolta (vedi sotto).

**Il testo esce dallo schermo, o la pagina è tutta bianca e senza stile.**
Manca la connessione a internet. La pagina si apre, ma senza l'impaginazione che
arriva da internet il testo non sta nella colonna. Controlla la connessione e
ricarica con <kbd>Cmd</kbd>+<kbd>R</kbd>.

## 5. Aggiungere altri ricordi (facoltativo, per chi se la sente)

Si fa in due passi.

1. **Raccogliere** dal browser: apri la pagina Facebook, premi
   <kbd>Cmd</kbd>+<kbd>Opt</kbd>+<kbd>J</kbd>, incolla tutto il contenuto di
   `console/fb_scrape_console.js`, premi <kbd>Invio</kbd>, poi scrivi
   `fbScrape.run()` e premi <kbd>Invio</kbd>. Quando ha finito, scrivi
   `fbScrape.saveJSON()`: si scarica un file `fb_posts_....json` nella cartella
   *Download*.
2. **Importare** dal Terminale (nella cartella dei ricordi):

   ```
   python3 import_console_dump.py ~/Downloads/fb_posts_NOME_DEL_FILE.json
   ```

   Si possono passare più file in una volta:

   ```
   python3 import_console_dump.py ~/Downloads/fb_posts_ricerca_*.json ~/Downloads/fb_posts_feed_*.json
   ```

   L'importazione è una **fusione**, non un'aggiunta: i ricordi già presenti
   vengono aggiornati (un messaggio intero sostituisce l'anteprima tagliata da
   Facebook, un collegamento fresco sostituisce una foto scaduta) e solo quelli
   nuovi vengono aggiunti in fondo. Rilanciare lo stesso file non cambia niente.
   Le foto vengono scaricate nella cartella giusta. Se compare il messaggio che
   manca `playwright`, si può importare solo il testo con `--media none`, oppure
   installarlo una volta sola:

   ```
   python3 -m venv .venv
   ./.venv/bin/pip install -r requirements.txt
   ./.venv/bin/python import_console_dump.py ~/Downloads/fb_posts_NOME_DEL_FILE.json
   ```

Istruzioni più dettagliate per la raccolta Facebook: `console/README.md`.

### Aggiungere i post di una raccolta Instagram

È disponibile anche `console/ig_scrape_console.js`, da incollare nella Console
della raccolta aperta su Instagram. Prima prova tre post:

```js
await igScrape.run({ maxPosts: 3, collectionName: 'Annibale' })
igScrape.saveJSON()
```

Il JSON si importa con lo stesso `import_console_dump.py` usato per Facebook.
L'importatore distingue i post Instagram ed evita duplicati tra acquisizioni
successive. Con `--dry-run` puoi vedere cosa cambierebbe senza scrivere file.

Procedura completa, ripresa dopo un'interruzione e limiti su caroselli e reel:
[Raccogliere da Instagram](console/INSTAGRAM.md). Il campione serve a verificare
la compatibilità con la pagina Instagram reale prima di raccogliere tutto.

La raccolta del 27 ottobre 2026 è stata integrata con `integrate_instagram.py`:
83 post Instagram, 27 corrispondenze unite a Facebook, un comunicato duplicato
tra due account Instagram e 55 nuovi ricordi. Foto e sei video sono salvati
localmente in `data/media/`; le versioni originali dei testi e i riferimenti
alle fonti sono conservati nei campi `sources` dei ricordi uniti.
La copia portabile della raccolta e le corrispondenze verificate si trovano in
`instagram/import/`; tutti i media referenziati sono inclusi in `data/media/`.

Il comando senza opzioni mostra soltanto il piano. `--apply` richiede il file
di corrispondenze già verificato, salva prima tutti i media, crea una copia di
sicurezza in `.backups/` e aggiorna JSONL e CSV. Non pubblica il sito. Ripetere
l'integrazione con gli stessi post non aggiunge altre copie.

> Le foto di Facebook sono collegate da indirizzi che scadono dopo pochi giorni:
> se raccogli i messaggi, importali lo stesso giorno.

## 6. Una nota

I messaggi e le foto sono di chi li ha scritti: questa presentazione serve per
ricordare Annibale tra noi, non per essere pubblicata altrove.
