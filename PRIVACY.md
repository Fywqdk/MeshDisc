# Privatlivspolitik for MeshDisc

*Gældende fra 24. oktober 2026*

Denne politik beskriver, hvilke data Discord-botten MeshDisc behandler. Kort sagt: botten gemmer ingen personoplysninger om Discord-brugere.

## Data fra Discord

- Botten bruger kun Discords standard-intents og har **ikke** adgang til indholdet af beskeder skrevet i Discord.
- Når du bruger `/mesh status` eller `/mesh pause`, behandler botten kommandoen og svarer kun dig. Dit bruger-ID, navn eller andre oplysninger gemmes ikke.
- Botten kender navnet og ID'et på de servere og kanaler, den er inviteret til, for at kunne poste. Det gemmes ikke ud over den kørende proces.

## Data fra MeshCore-netværket

Botten modtager radiopakker, som en MeshCore-node hører. For beskeder i kanaler, den er sat op til at læse, poster den i Discord:

- afsenderens navn, som afsenderen selv har valgt på sin node
- beskedens tekst og tidspunkt
- kanalens navn
- tekniske oplysninger: signalstyrke (SNR/RSSI), antal hop og rutens repeater-ID'er

Det er beskeder sendt i kanaler, som alle med kanalens navn eller nøgle kan læse. Beskeder i kanaler, botten ikke har nøglen til, samt direkte beskeder, kan ikke læses og postes ikke.

## Opbevaring

- Botten har ingen database. Statistik og et kortvarigt dublet-filter (som standard 60 sekunder) ligger kun i hukommelsen og forsvinder ved genstart.
- Driftslogs kan indeholde tekniske fejlbeskeder, men ikke Discord-brugeres oplysninger.
- Beskeder, der er postet i Discord, opbevares af Discord efter [Discords privatlivspolitik](https://discord.com/privacy) og kan slettes af serverens moderatorer.

## Deling

Data sælges eller deles ikke med tredjepart. Ud over Discord sendes intet nogen steder hen.

## Dine rettigheder

Ønsker du en besked fjernet fra Discord-kanalen, så kontakt serverens moderatorer. Spørgsmål om denne politik kan stilles ved at oprette et issue på [github.com/Fywqdk/MeshDisc](https://github.com/Fywqdk/MeshDisc/issues).

## Ændringer

Politikken kan blive opdateret. Den gældende version findes altid i dette repository, og ændringer kan ses i historikken.
