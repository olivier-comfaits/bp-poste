USE laposte_bp;

INSERT INTO porteurs (id, nom, prenom, entite, fonction, email, maturite) VALUES
(1, 'Morel',     'Camille',  'DRH Groupe',                    'Directrice mobilité interne',        'camille.morel@laposte.fr', 5),
(2, 'Benali',    'Karim',    'Branche Services-Courrier-Colis','Chef de projet Facteo',              'karim.benali@laposte.fr', 4),
(3, 'Lefèvre',   'Sophie',   'Colis & Logistique',            'Responsable innovation last-mile',    'sophie.lefevre@laposte.fr', 4),
(4, 'Nguyen',    'Minh',     'Branche Numérique',             'Product Owner applications client',   'minh.nguyen@laposte.fr', 3),
(5, 'Diallo',    'Aïcha',    'Réseau & Territoires',          'Directrice de projet territorial',    'aicha.diallo@laposte.fr', 5),
(6, 'Rossi',     'Julien',   'Direction RSE Groupe',          'Chef de projet décarbonation',        'julien.rossi@laposte.fr', 4),
(7, 'Haddad',    'Leila',    'La Banque Postale / LBP',       'Intrapreneure services seniors',      'leila.haddad@labanquepostale.fr', 3),
(8, 'Petit',     'Antoine',  'Direction de l''Innovation',    'Responsable valorisation innovation', 'antoine.petit@laposte.fr', 4);

INSERT INTO projets
(id, code, nom, typologie, branche, description, porteur_id, date_creation, duree_mois, statut,
 alignement_groupe, impact_branches, complexite_operationnelle, maturite_technique,
 impact_social, impact_environnemental, risque_technique, risque_humain, risque_reglementaire,
 investissement_k_eur, ca_annee_1_k, ca_annee_3_k, roi_pct, delai_retour_mois) VALUES

(1, 'BP-RH-01',
 'Mobilité interne augmentée',
 'RH', 'Groupe',
 'Outil intelligent de matching compétences / offres internes (IA générative + MySQL RH) pour fluidifier la mobilité, valoriser soft skills et mad skills, et réduire les recrutements informels.',
 1, '2026-03-12', 14, 'soumis',
 5, 5, 3, 4, 5, 2, 2, 3, 4,
 820, 0, 2100, 18.5, 20),

(2, 'BP-FAC-02',
 'Facteo Assist — copilote terrain du facteur',
 'digital', 'Courrier',
 'Assistant conversationnel embarqué sur le smartphone Facteo : aide au tri des tournées, scripts relation client, détection d''anomalies colis, et remontée terrain structurée.',
 2, '2026-02-04', 18, 'soumis',
 5, 4, 4, 4, 4, 3, 3, 4, 3,
 1450, 180, 3200, 22.0, 22),

(3, 'BP-LOG-03',
 'OptiLast — optimisation last-mile urbaine',
 'logistique', 'Colis',
 'Moteur d''optimisation des tournées urbaines combinant contraintes RSE (émissions), fenêtres clients et densité de points de retrait. Cible : villes > 100 000 habitants.',
 3, '2026-01-20', 24, 'soumis',
 4, 4, 5, 3, 3, 5, 4, 3, 2,
 2680, 420, 6100, 16.0, 30),

(4, 'BP-CLI-04',
 'L''Appli Unique Client 2.0',
 'client', 'Numérique',
 'Refonte de l''application client grand public : parcours unifié Courrier / Colis / Banque / Identité numérique, avec recommandations personnalisées et suivi temps réel.',
 4, '2026-04-02', 20, 'brouillon',
 4, 5, 5, 3, 3, 2, 4, 3, 4,
 3900, 750, 8400, 12.5, 36),

(5, 'BP-TER-05',
 'Maison de services France Poste',
 'territorial', 'Réseau',
 'Concept de tiers-lieu postal dans 80 communes rurales : guichet multi-services (La Poste, CAF, Impôts, santé) + espace coworking + lockers. Valorise le rôle d''aménagement du territoire.',
 5, '2025-11-18', 30, 'soumis',
 5, 3, 4, 4, 5, 4, 2, 4, 3,
 5200, 310, 2800, 6.5, 48),

(6, 'BP-RSE-06',
 'Flotte douce 2030 — conversion vélos-cargo & VE',
 'RSE', 'Colis',
 'Plan d''accélération de conversion de 8 000 tournées urbaines vers vélo-cargo et véhicules électriques, avec outil de priorisation des sites et calcul d''impact carbone.',
 6, '2026-03-01', 36, 'soumis',
 5, 4, 4, 4, 4, 5, 3, 3, 2,
 7400, 0, 1900, 8.0, 42),

(7, 'BP-BAN-07',
 'SereniPoste — offre bundled seniors',
 'innovation', 'Banque',
 'Offre packagée (compte + assistance + coffre-fort numérique + passage facteur « veiller sur mes parents ») destinée aux 70+ et à leurs aidants. Logique d''intrapreneuriat LBP x Réseau.',
 7, '2026-05-10', 16, 'brouillon',
 4, 4, 3, 3, 5, 2, 3, 4, 5,
 980, 260, 2400, 19.0, 18),

(8, 'BP-INN-08',
 'InnovLab — portail de valorisation des PoC',
 'innovation', 'Groupe',
 'Plateforme interne de dépôt, scoring, incubateur et industrialisation des PoC. Objectif : réduire le taux de PoC « morts-nés » et accélérer le go / no-go Codir.',
 8, '2026-04-18', 12, 'soumis',
 5, 3, 2, 4, 3, 2, 2, 2, 2,
 540, 0, 1100, 24.0, 16);

-- 3 années d'hypothèses par projet (24 lignes) — montants en k€
INSERT INTO hypotheses_financieres
(projet_id, annee, postes_salaires_k, materiel_k, logiciel_k, charges_fiscales_k, frais_admin_k, autres_depenses_k,
 nb_clients, recette_p1_k, recette_p2_k, recette_p3_k, marge_brute_pct, ebe_k, resultat_exploitation_k, bfr_k, tresorerie_k) VALUES
-- BP-RH-01 : gains = recrutements évités + baisse turnover (valorisés en recettes internes)
(1,1, 420, 40, 180, 35, 28, 20,  12000, 180,  40,  0, 22, -380, -420,  40, -480),
(1,2, 310, 15,  90, 28, 22, 15,  28000, 620, 140, 40, 48,  210,  160,  55,  -90),
(1,3, 290, 10,  70, 32, 20, 12,  45000, 980, 220, 80, 58,  640,  580,  60,  410),
-- BP-FAC-02
(2,1, 680, 220, 260, 70, 45, 40,  18000, 120,  60,  0, 18, -720, -790,  90, -860),
(2,2, 540,  80, 140, 65, 40, 30,  42000, 980, 320, 80, 41,  280,  190, 110, -240),
(2,3, 510,  40, 110, 80, 38, 25,  62000, 1680,540,140, 52,  980,  860, 120,  520),
-- BP-LOG-03
(3,1, 980, 420, 510, 140, 80, 90,  8,   280, 140,  0, 16, -1280,-1410, 220,-1650),
(3,2, 860, 180, 260, 150, 75, 70,  22,  1420,680,180, 34,   320,  180, 260, -740),
(3,3, 820,  90, 180, 190, 70, 55,  45,  2780,1240,360, 46,  1480, 1260, 280,  390),
-- BP-CLI-04
(4,1, 1620, 180, 740, 210, 140, 120,  900000, 420, 220, 110, 14, -1980,-2210, 310,-2480),
(4,2, 1480,  80, 420, 230, 130,  90, 2100000, 1680,740,280, 29,   180,  -40, 340,-1260),
(4,3, 1390,  40, 280, 280, 120,  80, 3800000, 3360,1480,560, 38,  1620, 1380, 360,  240),
-- BP-TER-05
(5,1, 1860, 920, 180, 240, 210, 310,  12,  180,  80,  50, 11, -2860,-3120, 420,-3480),
(5,2, 1720, 280,  90, 250, 200, 240,  38,  620, 280, 160, 21, -1280,-1490, 390,-2140),
(5,3, 1680,  80,  70, 270, 190, 180,  80,  1180,520, 280, 28,  -240, -410, 370,-1180),
-- BP-RSE-06
(6,1, 980, 2840, 220, 180, 90, 140,  40,    0,   0,   0,  8, -4120,-4310, 180,-4580),
(6,2, 860, 1680, 140, 190, 85, 110,  140,  220, 180,  80, 16, -2140,-2320, 160,-2860),
(6,3, 820,  620,  90, 210, 80,  90,  280,  680, 540, 220, 24,  -180, -340, 150,-1240),
-- BP-BAN-07
(7,1, 410,  30, 160,  45, 35, 28,   8000, 180,  60,  20, 28, -280, -320,  70, -390),
(7,2, 360,  15,  80,  52, 32, 22,  24000, 620, 210,  80, 44,  240,  190,  85,  -40),
(7,3, 340,  10,  60,  68, 30, 18,  48000, 1180,420, 160, 51,  720,  650,  90,  540),
-- BP-INN-08
(8,1, 280,  20, 110,  18, 16, 12,   40,    40,  20,   0, 26, -180, -210,  20, -240),
(8,2, 220,  10,  50,  22, 14, 10,   90,   220,  80,  30, 49,  180,  150,  25,   20),
(8,3, 210,   5,  40,  28, 12,  8,  140,   420, 160,  60, 57,  420,  380,  25,  380);

INSERT INTO parametres_strategiques
(projet_id, priorite_groupe, avantage_concurrentiel, opportunite_marche, kpis, dependances) VALUES
(1, 'Marque employeur & fidélisation',
 'Matching multimodal (hard / soft / mad skills) absent des outils Bourse d''emplois et MaCarrière.',
 'Turnover des métiers en tension (informatique, data, relation client) ; obligation d''emploi interne prioritaire.',
 'Taux de mobilité interne ; délai moyen de pourvoi ; % offres pourvues en interne ; NPS collaborateurs.',
 'SIRH Groupe, Bourse d''emplois, référentiel compétences, RGPD / CNIL.'),
(2, 'Excellence opérationnelle du facteur',
 'Couche IA native dans l''outil déjà déployé (Facteo) — pas de nouvel hardware.',
 'Volume colis + exigences qualité distribution ; besoin d''aide en temps réel pour facteurs moins expérimentés.',
 'Productivité tournée ; taux d''anomalies ; temps de formation ; CSAT destinataires.',
 'DSI Facteo, organisations territoriales, organisations syndicales, formation.'),
(3, 'Performance colis & décarbonation',
 'Optimisation multi-objectifs (coût, délai, CO2) vs. moteurs mono-critère historiques.',
 'Croissance colis urbain et ZFE ; pression collectivités sur les émissions du last-mile.',
 'km par colis ; kgCO2e / colis ; taux de premier passage ; coût de tournée.',
 'TMS existant, données trafic, flotte, collectivités partenaires.'),
(4, 'Relation client omnicanale',
 'Parcours unique multi-métiers là où les apps sont encore silotées.',
 'Attentes clients type « super-app » ; identité numérique La Poste déjà reconnue.',
 'MAU ; taux de conversion ; tickets réduction centre d''appels ; NPS digital.',
 'LBP, Identité Numérique, DSI Groupe, conformité DSP2 / eIDAS.'),
(5, 'Aménagement du territoire / service universel',
 'Réseau physique unique en France ; confiance institutionnelle inégalée en rural.',
 'Fermeture de services publics de proximité ; France Services ; mairies demandeuses.',
 'Nb communes couvertes ; fréquentation ; recettes annexes ; satisfaction élus.',
 'État / France Services, collectivités, bailleurs, branches internes.'),
(6, 'Trajectoire nette zéro & entreprise à mission',
 'Taille de flotte et maillage : effet d''échelle que peu d''acteurs peuvent reproduire.',
 'ZFE, ADEME, taxonomie européenne, attentes investisseurs et collectivités.',
 'Part de tournées bas-carbone ; tCO2e évitées ; TCO flotte ; taux de dispo VE.',
 'Achats flotte, énergie, urbanisme des PEC, formation conducteurs.'),
(7, 'Silver économie & lien social',
 'Actif unique : le facteur qui passe déjà. Bundle bancaire + présence physique.',
 'Vieillissement, isolation des aidants, concurrence néobanques peu présentes sur ce segment.',
 'Nb packs souscrits ; taux d''équipement 70+ ; NPS aidants ; sinistralité assistance.',
 'LBP conformité, Réseau, partenaires assistance, ACPR.'),
(8, 'Accélération de l''innovation interne',
 'Industrialise le go/no-go au lieu de laisser les PoC mourir en silo.',
 'Volume croissant de PoC IA ; besoin Codir de comparabilité et de priorisation.',
 'Taux de PoC industrialisés ; délai go/no-go ; capital innovation alloué vs. consommé.',
 'Direction Innovation, Codir, DSI, juristes PI.');

INSERT INTO risques (projet_id, libelle, categorie, probabilite, impact, mitigation) VALUES
-- catalogue (projet_id NULL)
(NULL, 'Dérive de périmètre (scope creep)', 'operationnel', 4, 3, 'Gouvernance de cadrage mensuelle et freeze fonctionnel J+90.'),
(NULL, 'Indisponibilité des données sources', 'technique', 3, 4, 'Audit d''accessibilité data dès le cadrage + jeux synthétiques de secours.'),
(NULL, 'Rejet métier / conduite du changement insuffisante', 'humain', 4, 4, 'Sponsoring N-1 + ambassadeurs terrain + formation courte obligatoire.'),
(NULL, 'Non-conformité RGPD ou ACPR', 'reglementaire', 2, 5, 'Privacy by design, AIPD, revue juridique avant tout pilote.'),
(NULL, 'Surcoût infrastructure cloud / tokens IA', 'financier', 3, 3, 'Plafonds de tokens, cache, modèles distillant, observabilité coût.'),
(NULL, 'Dépendance à un unique fournisseur de LLM', 'technique', 3, 4, 'Couche d''abstraction multi-modèles (Claude / Mistral / Gemini).'),
(NULL, 'Hallucinations dans les livrables destinés au Codir', 'operationnel', 3, 5, 'Sortie JSON contrainte + validation humaine obligatoire avant export.'),
(NULL, 'Conflit social sur l''automatisation des tâches', 'humain', 3, 4, 'Dialogue social anticipé, IA positionnée en assistance et non substitution.'),
(NULL, 'Retard d''intégration au SI existant', 'technique', 4, 3, 'API contract-first et bouchons dès le sprint 1.'),
(NULL, 'Cannibalisation d''une offre existante', 'financier', 2, 3, 'Matrice offres / ciblage validée par le marketing branche.'),
-- risques liés aux projets
(1, 'Qualité hétérogène des fiches de poste et profils RH', 'technique', 4, 3, 'Enrichissement IA + revue humaine des 500 premiers matching.'),
(1, 'Crainte de fichage des soft skills', 'reglementaire', 3, 4, 'Consentement explicite, finalité limitée, droit d''opposition.'),
(2, 'Charge cognitive supplémentaire pour le facteur', 'humain', 4, 4, 'Mode « suggestion discrète », opt-in par tournée, tests UX facteurs.'),
(2, 'Couverture réseau insuffisante en rural', 'technique', 3, 3, 'Mode dégradé offline + synchronisation en fin de tournée.'),
(3, 'Données trafic / voirie incomplètes', 'technique', 4, 4, 'Partenariats collectivités + fallback historique de tournées.'),
(4, 'Complexité de convergence des SI branches', 'technique', 5, 5, 'Socle identité commun et ouverture progressive des parcours.'),
(5, 'Modèle économique fragile hors subventions', 'financier', 4, 4, 'Mix recettes (services, lockers, coworking) + conventions pluriannuelles.'),
(6, 'Capacité fournisseurs vélos-cargo / bornes', 'operationnel', 3, 4, 'Multi-sourcing européen et planning d''achat glissant 24 mois.'),
(7, 'Qualification ACPR d''une activité d''assurance de fait', 'reglementaire', 3, 5, 'Partenariat assureur agréé, pas d''activité d''assurance en propre.'),
(8, 'Faible adoption si le scoring est perçu comme punitif', 'humain', 3, 3, 'Score explicable, droit de réponse du porteur, usage d''aide à la décision.');

INSERT INTO opportunites (projet_id, libelle, categorie, potentiel, description) VALUES
(NULL, 'Effet vitrine entreprise à mission', 'image', 4, 'Tout projet à impact social ou environnemental mesurable nourrit le rapport de mission.'),
(NULL, 'Réutilisation d''un socle IA transverse', 'technique', 5, 'Les prompts, le score et le schéma MySQL sont réplicables sur d''autres cas RH / RSE.'),
(NULL, 'Financements publics (ADEME, France 2030, fonds européens)', 'financier', 4, 'Plusieurs typologies du portefeuille sont éligibles à des aides non dilutives.'),
(NULL, 'Data réseau unique en France', 'marche', 5, 'Le maillage et les flux colis / courrier constituent un actif difficilement copiable.'),
(NULL, 'Intrapreneuriat et marque employeur', 'humain', 3, 'Des PoC visibles renforcent l''attractivité des profils data / produit.'),
(1, 'Réduction du resorting externe sur métiers en tension', 'financier', 5, 'Chaque pourvoi interne évite 8 à 15 k€ de frais de recrutement et d''onboarding.'),
(2, 'Montée en compétence accélérée des facteurs saisonniers', 'operationnel', 4, 'Le copilote réduit le temps d''autonomie d''un saisonnier de plusieurs semaines.'),
(3, 'Contrats collectivités « logistique bas-carbone »', 'marche', 5, 'Différenciant commercial face à des pure-players moins ancrés localement.'),
(5, 'Conventions France Services et loyers symboliques', 'financier', 4, 'Le modèle s''équilibre si la collectivité porte une part du foncier.'),
(7, 'Cross-sell LBP x Réseau sur une cible peu digital-native', 'marche', 4, 'Le facteur devient prescripteur d''un pack, pas d''un produit bancaire isolé.');

INSERT INTO scenarios (projet_id, type_scenario, ca_3ans_k, resultat_3ans_k, roi_pct, hypotheses) VALUES
(1,'bas',    980,  -120,  4.0,  'Adoption 35 % des managers, matching imparfait, 1 800 mobilités / an.'),
(1,'median', 1860,   320, 18.5, 'Adoption 55 %, 3 400 mobilités / an, 25 % d''offres pourvues en interne.'),
(1,'haut',   2680,   740, 32.0, 'Adoption 75 %, intégration SIRH complète, 5 000 mobilités / an.'),
(2,'bas',    1480,  -210,  6.0,  'Déploiement 8 régions, usage réel 30 % des facteurs.'),
(2,'median', 3920,   260, 22.0, 'Déploiement national progressif, usage 55 %, -8 % d''anomalies.'),
(2,'haut',   6100,  1180, 38.0, 'Usage 75 %, ouverture API partenaires, module formation vendu en externe.'),
(3,'bas',    2480,  -640,  2.0,  '12 agglomérations, gains km limités à 6 %.'),
(3,'median', 6120,   30,  16.0, '28 agglomérations, -12 % km, -15 % CO2 last-mile.'),
(3,'haut',   8940,  1620, 28.0, '40 agglo + offre white-label collectivités.'),
(4,'bas',    2860, -1840, -4.0,  'Parcours partiels, 1,2 M MAU, cannibalisation limitée.'),
(4,'median', 8440,  -870, 12.5, 'Parcours unifié 3 branches, 3,8 M MAU, -12 % contacts CAPP.'),
(4,'haut',  12600,  1640, 21.0, '5,5 M MAU, marketplace services, identifiant unique citoyen.'),
(5,'bas',    1240, -2860, -8.0,  '35 sites, mix recettes faible, dépendance subventions > 60 %.'),
(5,'median', 2680, -5020,  6.5,  '80 sites, mix lockers + France Services, subventions 40 %.'),
(5,'haut',   4200, -2140, 14.0,  '120 sites, coworking saturé, conventions 8 ans.'),
(6,'bas',     420, -8120, -2.0,  '3 000 tournées converties, TCO VE défavorable.'),
(6,'median', 1620, -6970,  8.0,  '8 000 tournées, aides ADEME, TCO à parité en N+3.'),
(6,'haut',   3180, -4120, 15.0,  '12 000 tournées + revente d''expertise flotte douce.'),
(7,'bas',     860,  -140,  7.0,  '12 000 packs, friction conformité, faible relais facteurs.'),
(7,'median', 2460,   520, 19.0, '48 000 packs, 15 % des bureaux prescripteurs.'),
(7,'haut',   4120,  1280, 31.0, '90 000 packs, partenariat mutuelle, offre aidants entreprise.'),
(8,'bas',     280,   -80,  8.0,  '20 PoC / an, 10 % industrialisés.'),
(8,'median',  840,   320, 24.0, '45 PoC / an, 25 % industrialisés, budget innovation mieux alloué.'),
(8,'haut',   1420,   680, 41.0, '70 PoC / an, 35 % industrialisés, licence interne aux filiales.');
