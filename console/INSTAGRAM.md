# Aggiungere i ricordi salvati su Instagram

Il raccoglitore è [ig_scrape_console.js](ig_scrape_console.js). Si usa dalla
Console del browser, come quello Facebook, nella scheda dove hai già effettuato
l'accesso a Instagram. Non richiede plugin, password, token o installazioni.

La griglia dei salvati contiene miniature: lo script apre ogni post, legge ciò
che Instagram mostra, prova a scorrere il carosello e richiude il post per
continuare. Non modifica i salvati, non mette like e non invia messaggi.

## Prima prova: tre ricordi

1. Dal browser del Mac apri Instagram → **Salvati** → **la raccolta su Annibale**.
   Devi vedere la griglia della raccolta, senza un post aperto sopra.
2. Apri la Console: **⌘⌥J** su Chrome/Brave. Copia tutto il contenuto di
   `console/ig_scrape_console.js`, incollalo e premi Invio.
   Se il browser blocca l'incolla, segui l'indicazione della Console; su Chromium
   può chiedere di digitare `allow pasting`. L'incolla definisce i comandi:
   non avvia ancora la raccolta.
3. Avvia il campione:

   ```js
   await igScrape.run({ maxPosts: 3, collectionName: 'Annibale' })
   ```

4. Guarda i dati e scarica il JSON:

   ```js
   igScrape.posts()
   igScrape.status()
   igScrape.saveJSON()
   ```

Il file `ig_posts_....json` viene scaricato nei Download. Contiene i post, i
collegamenti scoperti, gli eventuali errori e l'indirizzo della raccolta.
Controlla che autore e testo siano quelli del post (senza commenti), e che un
carosello abbia tutte le foto prima di procedere con la raccolta completa.

**La compatibilità con la tua pagina Instagram va verificata con questo
campione.** I controlli automatici del progetto usano pagine di prova. Il 27
ottobre 2026 i selettori di lettura sono stati verificati anche sui tre post reali
di mossomilano, madre_project e piermaran nella raccolta Annibale, con testo,
autore, data e una foto ciascuno; apertura e chiusura sono state eseguite tramite
i controlli del browser dell'app. Il ciclo completo dalla Console non è stato
eseguito in quella verifica, perché il controllo dell'app consente solo
JavaScript di lettura. Se Instagram cambia struttura, apre una pagina intera
invece della finestra sopra la griglia o mostra un controllo di accesso, possono
servire modifiche ai selettori. Lo script si ferma al primo errore di lettura.
Per diagnosticare: `igScrape.inspect()` e gli avvisi della Console.

## Raccogliere gli altri e interrompere

Se il campione è corretto, nella stessa scheda:

```js
await igScrape.run({ maxPosts: 1000, collectionName: 'Annibale' })
igScrape.saveJSON()
```

`maxPosts` è il totale dei post raccolti, compresi quelli del campione. I tre
già acquisiti vengono saltati. Non cambiare scheda o navigare mentre lavora:
il browser rallenta le schede nascoste e lo script si ferma quando lo rileva.
Puoi interrompere dalla Console con:

```js
igScrape.stop()
```

Finisce la lettura in corso e tenta di tornare alla raccolta. Salva comunque
il JSON prima di chiudere la scheda. I dati vengono copiati anche nella memoria
locale di Instagram in questo browser; non sono sincronizzati tra dispositivi.

Se ricarichi la pagina, torna alla **stessa raccolta**, reincolla lo script e usa:

```js
igScrape.savedInfo()
igScrape.restore()
await igScrape.run({ maxPosts: 1000 })
igScrape.saveJSON()
```

Per una raccolta diversa, salva prima il JSON attuale, poi usa `igScrape.reset()`.
Il reset cancella sia i dati in memoria sia la copia locale del raccoglitore.

## Cosa è stato raccolto, cosa manca

- `igScrape.posts()` mostra solo post con testo o media effettivamente letti.
- `igScrape.links()` mostra anche i link non ancora letti o falliti. I link
  pendenti non vengono spacciati per ricordi completi e non vengono importati.
- `igScrape.status()` mostra quanti post hanno avvisi e il motivo dell'arresto.
  La fine della griglia caricata non prova che Instagram abbia mostrato tutti
  i post della raccolta: confronta il conteggio con quello che vedi in Instagram.
- `capture_warnings` segnala testo/autore non trovati, caroselli che non avanzano,
  limite delle diapositive o video senza URL diretto. Un testo vuoto può essere
  normale per una foto senza didascalia; non viene inventato.
- `carousel_complete` significa che non era visibile un altro pulsante Avanti:
  va confermato sul campione, perché un selettore cambiato può nascondere foto.

Per riprovare i post con avvisi nella stessa raccolta:

```js
igScrape.retryWarnings()
await igScrape.run({ maxPosts: 1000 })
igScrape.saveJSON()
```

Per riprendere soltanto i due caroselli con un video intermedio segnalati nella
raccolta del 27 ottobre, reincolla lo script aggiornato nella stessa scheda
(i post già in memoria restano presenti), poi esegui:

```js
igScrape.retryWarnings({ authors: ['piero_pelizzaro', 'fusacchia'] })
await igScrape.run({ maxPosts: 5000, maxScrolls: 1000, idleLimit: 12 })
igScrape.saveJSON('ig_annibale_recupero_caroselli')
```

Se hai ricaricato la pagina, usa prima `igScrape.restore()` dalla stessa
raccolta. La correzione permette di superare i video in streaming e acquisire
le foto successive; non trasforma il video in un file scaricabile. L'avviso
`carousel_did_not_advance` può quindi sparire lasciando
`video_stream_without_direct_url`, che descrive il contenuto ancora mancante.
Il JSON originale resta la copia di riferimento finché il nuovo export non è
stato controllato.

Altri comandi:

| Comando | Effetto |
| --- | --- |
| `igScrape.collectLinks()` | Memorizza i link delle miniature attualmente visibili. |
| `await igScrape.run({ linksOnly: true, maxPosts: 1000 })` | Scorre e raccoglie solo link: non basta per importare testi/foto. |
| `await igScrape.dump()` | Legge il singolo post aperto e salva il JSON, senza tornare alla griglia. |
| `igScrape.persist()` | Aggiorna subito la copia locale. |

Le opzioni `delayMin` e `delayMax` regolano le pause; `timeout` l'attesa per un
post; `maxScrolls` e `idleLimit` limitano gli scorrimenti; `maxSlides` limita il
carosello (30 di default). Sono limiti di lavoro, non garanzie di completezza.

## Importare nel progetto

Dal Terminale, dentro la cartella del progetto, controlla prima cosa cambierebbe:

```sh
python3 import_console_dump.py ~/Downloads/ig_posts_NOME_DEL_FILE.json --dry-run
```

Poi importa e scarica le immagini con l'ambiente Python del progetto:

```sh
./.venv/bin/python import_console_dump.py ~/Downloads/ig_posts_NOME_DEL_FILE.json
```

Se l'ambiente non è ancora configurato, segui il README principale. Per importare
solo i dati, senza dipendenze e senza scaricare media:

```sh
python3 import_console_dump.py ~/Downloads/ig_posts_NOME_DEL_FILE.json --media none
```

Puoi passare più JSON, anche insieme ai dump Facebook. L'identità Instagram
dipende dal codice del post (`ig_...`), così una nuova raccolta dello stesso post
non aggiunge duplicati. Post diversi con la stessa didascalia restano distinti;
una copia su Facebook resta separata finché non viene integrata usando le
corrispondenze verificate. Per la raccolta del 27 ottobre è stato usato
`integrate_instagram.py`, che conserva un solo ricordo con entrambe le fonti,
le versioni originali dei testi e l'unione dei media. L'importatore riconosce
anche gli identificativi Instagram già associati a un ricordo Facebook.

Importa presto: gli indirizzi delle immagini possono scadere. Le immagini salvate
localmente vengono mantenute quando arrivano URL nuovi. Gli errori di download
restano nei dati (`download_error`); un post con lo stesso URL già fallito non
viene ritentato automaticamente. Una nuova acquisizione con URL aggiornati
permette un nuovo tentativo.

Per i video si può usare `--media all`, ma si scaricano solo URL diretti:
stream/blob senza un file accessibile sono segnalati. La presentazione mostra
foto e video con un file disponibile nella stessa galleria, con i controlli
nativi del lettore e i collegamenti alle fonti originali. I sei video della
raccolta corrente sono stati recuperati con yt-dlp e salvati in `data/media/`.

Questi comandi aggiornano i file locali. Non eseguono push e non pubblicano il
sito. I JSON possono contenere post visibili soltanto al tuo account: conserva
gli originali in un luogo adatto, fuori dalla cartella pubblica del sito.
