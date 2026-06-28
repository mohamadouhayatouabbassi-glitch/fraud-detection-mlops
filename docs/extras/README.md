# Documents annexes

Documents complémentaires au projet de détection de fraude. Ne sont pas
indispensables au fonctionnement du service.

## `Feuilles_de_route_Projets_Fintech.pdf`

Document de planification listant **70 idées de projets fintech** sous
forme de feuilles de route prêtes à attaquer. Chaque projet contient :

- niveau requis (JUNIOR / INTERMÉDIAIRE / SENIOR)
- durée estimée
- problème métier
- feuille de route en 4 phases
- stack technique recommandée
- prérequis et compétences clés

19 verticales couvertes : risque/fraude, crédit, AML/KYC, client,
cybersécurité, plateforme interne, insurtech, wealth, B2B/corporate,
crypto, paiements, regtech, climat & ESG, open banking, BaaS,
cross-border, proptech, tax, identité.

### Régénération

```bash
pip install ".[docs]"
python scripts/generate_roadmaps_pdf.py
```

Le PDF est généré dans `docs/Feuilles_de_route_Projets_Fintech.pdf`
(à déplacer ensuite dans `docs/extras/` si on souhaite le committer).
