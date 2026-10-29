# Ricordi per Annibale — come si guarda

Questa cartella contiene una presentazione a schermo intero con tutti i
messaggi e le foto raccolti da Facebook.

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
- Se un ricordo non ha foto, il testo occupa tutto lo spazio.
- In alto a destra c'è il conteggio, ad esempio `12 / 248`.
- Dietro le parole si muove uno sfondo di colore e polvere di luce: è solo
  decorazione. Se il sistema è impostato per ridurre le animazioni
  (*Impostazioni → Accessibilità → Movimento*), lo sfondo resta fermo; se il
  computer non sa disegnarlo, la pagina resta scura com'era prima.
  Per spegnerlo del tutto, aggiungi `?aura=off` in fondo all'indirizzo
  (`.../index.html?aura=off`): la pagina torna nera, senza sfondo colorato.

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

Nei due pulsanti al centro dell'intestazione ci si sposta tra le sezioni:
**Ricordi** (la presentazione) e **Video**. Su uno schermo stretto finiscono su
una riga tutta loro, sempre al centro. La pagina dei video raccoglie gli
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
data/excluded.json        ← i post tolti di proposito (non devono tornare)
```

La cartella si può copiare dove vuoi (anche su una chiavetta), ma
`index.html` deve restare dentro la cartella insieme a `data/`:
se lo sposti da solo, le foto non si trovano più.

Le altre cose (`console/`, `import_console_dump.py`, `import_thoughts.py`,
`fbstore.py`, `remove_posts.py`, `requirements.txt`) servono solo se un giorno si
vogliono raccogliere altri ricordi o importare i pensieri lasciati sul sito. Per
guardare la presentazione non servono.

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

## 5. Lasciare un pensiero dal sito

Chi visita la presentazione può scrivere il proprio ricordo senza avere un
account: in alto, accanto a **Ricordi** e **Video**, c'è **Lascia un pensiero**.

1. Si compila il modulo: nome, pensiero, una foto se si vuole, email
   facoltativa.
2. Il pensiero **non compare subito**: arriva a chi cura il sito, che lo legge e
   decide se pubblicarlo.
3. Una volta approvato, si esporta il foglio delle risposte da Tally e si importa
   dal Terminale:

   ```
   python3 import_thoughts.py ~/Downloads/tally-export.csv
   ```

   Lo script aggiunge i pensieri a `data/posts.jsonl`, scarica le foto in
   `data/media/` e rigenera `data/posts.csv`. Rilanciare lo stesso file non crea
   doppioni, e con `--dry-run` si vede cosa succederebbe senza scrivere niente.
   L'email non viene mai salvata: resta solo in Tally.

### Preparare il modulo (una volta sola)

1. Creare un modulo gratuito su tally.so con cinque campi: **Nome o come vuoi
   firmarti** (obbligatorio), **Il tuo pensiero per Annibale** (obbligatorio),
   **Una foto** (facoltativa, un file), **La tua email** (facoltativa),
   **Consenso alla pubblicazione** (obbligatorio).
2. Nelle impostazioni del modulo: notifica via email a ogni risposta, tema scuro,
   “Prevent duplicate submissions”.
3. Copiare il link di incorporamento (Share → Embed) e incollarlo nella costante
   `FORM_URL` in fondo a `index.html`, aggiungendo in coda
   `?hideTitle=1&transparentBackground=1&alignLeft=1`. Finché è vuota, il
   pulsante resta nascosto e nessun dato esce dal sito.
4. Se vuoi indicare un indirizzo a cui chiedere la rimozione di un pensiero,
   scrivilo in `THOUGHTS_CONTACT`, sempre in fondo a `index.html`.

Per esportare solo i pensieri approvati: nel pannello Tally si scelgono le
risposte e si esporta il CSV (oppure si usa l'integrazione con Google Sheets e si
scarica il foglio). Le risposte restano sui server di Tally, che è un fornitore
europeo; se il CSV ha una colonna **Approvato**, lo script importa solo le righe
con “sì”.

## 6. Aggiungere altri ricordi (facoltativo, per chi se la sente)

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
   Un messaggio già completo non viene mai riscritto: se correggi a mano una
   parola in `data/posts.jsonl`, l'importazione la lascia com'è.
   Le foto vengono scaricate nella cartella giusta. Se compare il messaggio che
   manca `playwright`, si può importare solo il testo con `--media none`, oppure
   installarlo una volta sola:

   ```
   python3 -m venv .venv
   ./.venv/bin/pip install -r requirements.txt
   ./.venv/bin/python import_console_dump.py ~/Downloads/fb_posts_NOME_DEL_FILE.json
   ```

Istruzioni più dettagliate per la raccolta: `console/README.md`.

> Le foto di Facebook sono collegate da indirizzi che scadono dopo pochi giorni:
> se raccogli i messaggi, importali lo stesso giorno.

## 7. Togliere un ricordo

Se un post non c'entra (un augurio di compleanno, una pubblicità, un post che
non è un ricordo), si toglie così, copiando l'identificativo dall'indirizzo
(`...#fb_10237650532620953`):

```
python3 remove_posts.py fb_10237650532620953 --reason "auguri di compleanno"
```

Si possono togliere più post in una volta, elencandoli. Il post sparisce dalla
presentazione, la sua cartella di foto viene cancellata e l'identificativo
finisce in `data/excluded.json`: così, se un giorno si reimporta lo stesso file
di Facebook, quel post **non torna**. `data/excluded.json` va tenuto insieme
agli altri dati.

Vale anche per i pensieri arrivati dal sito (gli identificativi cominciano con
`site_`): si tolgono con lo stesso comando e, reimportando lo stesso CSV, non
tornano.

## 8. Una nota

I messaggi e le foto sono di chi li ha scritti: questa presentazione serve per
ricordare Annibale tra noi, non per essere pubblicata altrove. Anche i pensieri
lasciati dal sito vengono pubblicati solo con il consenso di chi li scrive, e
chiunque può chiederne la rimozione.
