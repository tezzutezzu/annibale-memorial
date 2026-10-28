# Raccogliere i ricordi da Facebook

`fb_scrape_console.js` legge i messaggi dalla pagina Facebook che hai già aperto
nel browser. Non serve installare niente: si incolla nella **Console** del
browser, uno strumento che Chrome ha già dentro.

Funziona con la sessione del browser, cioè con il tuo accesso: vede solo quello
che vedi tu. Non fa login al posto tuo e non tocca il tuo profilo Facebook.

Le foto non vengono scaricate qui (Chrome blocca i download automatici): il file
che ottieni contiene i messaggi e i collegamenti alle foto, e le foto vere si
scaricano dopo con `import_console_dump.py` (vedi il README principale).

---

## Come si parte

1. Apri la pagina che vuoi raccogliere: il profilo, un gruppo, i risultati di una
   ricerca, la home.
2. Premi <kbd>Cmd</kbd>+<kbd>Opt</kbd>+<kbd>J</kbd> per aprire la Console. (In
   alternativa: menu *Visualizza → Sviluppatore → Console JavaScript*.)
3. La prima volta Chrome blocca il testo incollato: scrivi `allow pasting` e premi
   <kbd>Invio</kbd>.
4. Copia **tutto** il contenuto di `fb_scrape_console.js`, incollalo nella Console
   e premi <kbd>Invio</kbd>. Non succede niente: viene solo caricato il comando,
   che userai al punto dopo.
5. Scrivi `fbScrape.run()` e premi <kbd>Invio</kbd>. La pagina comincia a scorrere
   da sola e la Console mostra l'avanzamento:

   ```
   [fbScrape] round 004  +6  total 31  idle 0/8
   ```

   `total` è quanti ricordi ha raccolto finora. `idle` conta gli scorrimenti di
   fila senza niente di nuovo.
6. Quando ha finito, **salvali in un file**:

   ```js
   fbScrape.saveJSON()
   ```

   Si scarica `fb_posts_<data>.json` nella cartella *Download*. È quel file che
   serve per l'importazione.

> `run()` non salva da solo: alla fine lo ricorda in Console scrivendo
> `next: fbScrape.saveJSON()`. Se chiudi la pagina prima di salvarlo, il lavoro
> resta solo nella memoria della pagina.

## I due modi di raccogliere

| comando | cosa fa |
| --- | --- |
| `fbScrape.run()` | **consigliato.** Scorre la pagina e raccoglie man mano. |
| `fbScrape.dump()` | Salva solo quello che è già nella pagina in questo momento, senza scorrere. Scarica il file da solo. |

`dump()` serve se hai già scorso la pagina a mano. Attenzione però: Facebook
toglie dalla pagina i messaggi che sono molto in alto, quindi il DOM contiene solo
una finestra di messaggi (spesso 15–40), non tutti quelli che hai visto passando.
`dump()` scrive quanti ne ha trovati:

```
[fbScrape] dump: 24 in the DOM, 24 new, 24 collected in total
```

Se il numero è più basso di quello che ti aspettavi, gli altri non sono più nella
pagina e non si possono leggere: usa `run()`, che li cattura mentre sono ancora
visibili.

## Post condivisi

Chi ricorda Annibale spesso non lo nomina: condivide il post di qualcun altro, che
lo nomina. Quei post vengono raccolti lo stesso, e il testo citato finisce in due
campi separati:

| campo | cosa contiene |
| --- | --- |
| `text` | quello che ha scritto chi condivide |
| `shared_author` | chi ha scritto il post condiviso |
| `shared_text` | il testo del post condiviso |

Per cercare un nome conviene guardare tutti e due i campi. Nella presentazione il
testo citato compare in fondo alla slide, dopo una freccia `↪`.

## Pulizia

Alla fine di `run()` (e di `dump()`) la raccolta si ripulisce da sola. Si
**cancella** solo quello che non è un post:

| cosa viene tolto | perché |
| --- | --- |
| post sponsorizzati | non sono ricordi |
| post senza testo, senza testo citato e senza foto | non mostrano niente |

Il resto non si cancella: si **marca**. Ogni post riceve `relevant`:

| valore | significato |
| --- | --- |
| `true` | il nome compare, oppure il testo ha parole da ricordo ("mancherai", "Bollenti Spiriti", "non ci credo che te ne sia andato"…) |
| `false` | viene dal **feed** e non ha nessuno dei due: la presentazione lo nasconde, il dato resta nel `.jsonl` |
| assente | non giudicabile: post di una ricerca o di un profilo, oppure solo foto |

La distinzione conta: un ricordo spesso non scrive il nome ("Un abbraccio
grandissimo alla moglie Alessia…"). Un filtro per nome secco ne ha cancellati
cinque veri, per questo ora si nasconde e non si distrugge. Ogni post porta anche
`source` (`feed`, `search`, `post`, `page`): solo il feed viene marcato.

Per rivedere tutto, anche il rumore: `fbScrape.clean()` non cancella i marcati, e
`fbScrape.relevant(post)` dice cosa ne pensa la regola.

## Tutti i comandi

| comando | cosa fa |
| --- | --- |
| `fbScrape.run(opzioni)` | inizia (o riprende) la raccolta |
| `fbScrape.dump()` | salva subito quello che c'è nella pagina, e scarica il file |
| `fbScrape.stop()` | ferma la raccolta dopo il giro in corso |
| `fbScrape.saveJSON()` | scarica il file `.json` (quello che serve per importare) |
| `fbScrape.saveCSV()` | scarica la versione foglio di calcolo |
| `fbScrape.copyJSON()` | copia il JSON negli appunti |
| `fbScrape.posts()` | l'elenco dei ricordi raccolti finora |
| `fbScrape.restore()` | recupera la raccolta dopo un ricaricamento della pagina |
| `fbScrape.savedInfo()` | dice se c'è una raccolta salvata, quanti ricordi e quando |
| `fbScrape.clearSaved()` | cancella la copia salvata |
| `fbScrape.reset()` | ricomincia da zero (cancella anche la copia salvata) |
| `fbScrape.extract()` | legge la pagina una volta sola, senza scorrere |

## Regolare la raccolta

Di solito non serve toccare niente: i valori predefiniti vanno bene fino a 500
ricordi. Se ti servono più ricordi:

```js
fbScrape.run({ maxPosts: 1000, idleLimit: 15, delayMin: 2000, delayMax: 3500 })
```

| opzione | predefinito | a cosa serve |
| --- | --- | --- |
| `maxPosts` | 500 | quanti ricordi fermarsi a raccogliere |
| `maxScrolls` | 300 | quanti scorrimenti al massimo |
| `idleLimit` | 8 | si ferma dopo N scorrimenti senza niente di nuovo |
| `delayMin` / `delayMax` | 1200 / 2800 ms | pausa fra uno scorrimento e l'altro |

- **`idleLimit` è la cosa da alzare per prima.** Su ricerche e pagine lente
  capita di fare diversi scorrimenti a vuoto mentre Facebook carica il resto: se
  la raccolta si ferma troppo presto, aumenta questo numero.
- **`maxScrolls`** serve quando ogni scorrimento porta solo 1–2 ricordi: alzalo
  per pagine molto lunghe.
- **Più lento è più sicuro.** Per raccolte lunghe allunga la pausa invece di
  martellare la pagina.
- **Tieni la scheda in primo piano.** Chrome rallenta i timer delle schede in
  secondo piano e le pause si allungano.

## Se qualcosa va storto

**Ho ricaricato la pagina e ho perso tutto.** La raccolta viene salvata nella
memoria del browser ogni pochi secondi. Dopo aver ricaricato e reincollato il
file, scrivi:

```js
fbScrape.restore()
```

**La Console avvisa che lo spazio è finito.** La copia salvata si ferma intorno ai
4 MB di JSON (più o meno 1000–2000 ricordi): da lì in poi bisogna salvare il file
con `fbScrape.saveJSON()`.

**La Console avvisa che qualche post finisce con "…".** Significa che Facebook non
ha aperto il pulsante "Altro..." di quel messaggio: il testo salvato è il
riassunto, non il post intero. Tieni la scheda in primo piano, ricarica e riprova;
per i singoli post ostinati aprili e usa `fbScrape.dump()`. All'import il testo
completo sostituisce il riassunto.

**La raccolta si ferma sempre allo stesso punto.** Di solito è Facebook che ha
finito i risultati (una ricerca finisce, una pagina smette di caricare), non un
errore dello script: salva con `saveJSON()`, importa, e se serve riparti con un
altro giro.

## Due cose che sembrano strane ma sono volute

- **Riparte sempre dall'inizio** (`startFromTop`). I messaggi vengono disegnati
  solo quando passano davanti allo schermo: partendo a metà pagina si perderebbe
  in silenzio tutto quello che sta sopra.
- **Scorre di una schermata alla volta** (`stepRatio` 0.9). Saltare in fondo
  salterebbe i messaggi intermedi, che non verrebbero mai disegnati e quindi mai
  letti.

I risultati di una ricerca, poi, non sono nella pagina come i normali messaggi:
lo script li riconosce lo stesso, non devi fare niente.

## (Avanzato) Mandare i comandi dal Terminale

Se preferisci non incollare, puoi far eseguire il codice dal Terminale: apri
*Visualizza → Sviluppatore → Consenti JavaScript dagli eventi Apple*, poi:

```bash
osascript -e 'tell application "Google Chrome" to execute (active tab of front window) javascript "fbScrape.posts().length"'
```

Così si può caricare lo script da disco, avviare `fbScrape.run(...)`, controllare
ogni tanto quanti ricordi ci sono e scrivere il risultato direttamente in un file.
Quando hai finito **rimetti quell'impostazione su off**: finché è attiva, qualsiasi
script del computer può comandare quella scheda.
