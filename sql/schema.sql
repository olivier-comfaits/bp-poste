-- PostePlan IA — schéma MySQL / MariaDB
-- Executive MBA Epitech P2026 — Module SI et big data

CREATE DATABASE IF NOT EXISTS laposte_bp
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE laposte_bp;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS generations;
DROP TABLE IF EXISTS scenarios;
DROP TABLE IF EXISTS opportunites;
DROP TABLE IF EXISTS risques;
DROP TABLE IF EXISTS parametres_strategiques;
DROP TABLE IF EXISTS hypotheses_financieres;
DROP TABLE IF EXISTS projets;
DROP TABLE IF EXISTS porteurs;
SET FOREIGN_KEY_CHECKS = 1;

CREATE TABLE porteurs (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  nom           VARCHAR(120) NOT NULL,
  prenom        VARCHAR(120) NOT NULL,
  entite        VARCHAR(140) NOT NULL,
  fonction      VARCHAR(140) NOT NULL,
  email         VARCHAR(180),
  maturite      TINYINT NOT NULL DEFAULT 3 COMMENT '1=junior ... 5=expert projet',
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE projets (
  id                         INT AUTO_INCREMENT PRIMARY KEY,
  code                       VARCHAR(24) NOT NULL UNIQUE,
  nom                        VARCHAR(220) NOT NULL,
  typologie                  VARCHAR(80)  NOT NULL COMMENT 'RH, digital, logistique, territorial, client, RSE, innovation',
  branche                    VARCHAR(80)  NOT NULL COMMENT 'Courrier, Colis, Banque, Réseau, Numérique, Groupe',
  description                TEXT,
  porteur_id                 INT,
  date_creation              DATE,
  duree_mois                 INT NOT NULL DEFAULT 18,
  statut                     VARCHAR(40) NOT NULL DEFAULT 'brouillon',
  alignement_groupe          TINYINT NOT NULL DEFAULT 3 COMMENT '1-5',
  impact_branches            TINYINT NOT NULL DEFAULT 3,
  complexite_operationnelle  TINYINT NOT NULL DEFAULT 3 COMMENT '1=simple 5=très complexe',
  maturite_technique         TINYINT NOT NULL DEFAULT 3,
  impact_social              TINYINT NOT NULL DEFAULT 3,
  impact_environnemental     TINYINT NOT NULL DEFAULT 3,
  risque_technique           TINYINT NOT NULL DEFAULT 3 COMMENT '1=faible 5=élevé',
  risque_humain              TINYINT NOT NULL DEFAULT 3,
  risque_reglementaire       TINYINT NOT NULL DEFAULT 3,
  investissement_k_eur       DECIMAL(12,2) NOT NULL DEFAULT 0,
  ca_annee_1_k               DECIMAL(12,2) NOT NULL DEFAULT 0,
  ca_annee_3_k               DECIMAL(12,2) NOT NULL DEFAULT 0,
  roi_pct                    DECIMAL(8,2)  NOT NULL DEFAULT 0,
  delai_retour_mois          INT NOT NULL DEFAULT 24,
  score_pertinence           DECIMAL(5,2) DEFAULT NULL,
  created_at                 TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_projet_porteur FOREIGN KEY (porteur_id) REFERENCES porteurs(id)
) ENGINE=InnoDB;

CREATE TABLE hypotheses_financieres (
  id                    INT AUTO_INCREMENT PRIMARY KEY,
  projet_id             INT NOT NULL,
  annee                 TINYINT NOT NULL COMMENT '1, 2 ou 3',
  postes_salaires_k     DECIMAL(12,2) NOT NULL DEFAULT 0,
  materiel_k            DECIMAL(12,2) NOT NULL DEFAULT 0,
  logiciel_k            DECIMAL(12,2) NOT NULL DEFAULT 0,
  charges_fiscales_k    DECIMAL(12,2) NOT NULL DEFAULT 0,
  frais_admin_k         DECIMAL(12,2) NOT NULL DEFAULT 0,
  autres_depenses_k     DECIMAL(12,2) NOT NULL DEFAULT 0,
  nb_clients            INT NOT NULL DEFAULT 0,
  recette_p1_k          DECIMAL(12,2) NOT NULL DEFAULT 0,
  recette_p2_k          DECIMAL(12,2) NOT NULL DEFAULT 0,
  recette_p3_k          DECIMAL(12,2) NOT NULL DEFAULT 0,
  marge_brute_pct       DECIMAL(5,2)  NOT NULL DEFAULT 0,
  ebe_k                 DECIMAL(12,2) NOT NULL DEFAULT 0,
  resultat_exploitation_k DECIMAL(12,2) NOT NULL DEFAULT 0,
  bfr_k                 DECIMAL(12,2) NOT NULL DEFAULT 0,
  tresorerie_k          DECIMAL(12,2) NOT NULL DEFAULT 0,
  UNIQUE KEY uq_hypo (projet_id, annee),
  CONSTRAINT fk_hypo_projet FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE parametres_strategiques (
  id                      INT AUTO_INCREMENT PRIMARY KEY,
  projet_id               INT NOT NULL UNIQUE,
  priorite_groupe         VARCHAR(180),
  avantage_concurrentiel  TEXT,
  opportunite_marche      TEXT,
  kpis                    TEXT,
  dependances             TEXT,
  CONSTRAINT fk_param_projet FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE risques (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  projet_id     INT NULL COMMENT 'NULL = risque type du catalogue',
  libelle       VARCHAR(220) NOT NULL,
  categorie     VARCHAR(80)  NOT NULL COMMENT 'technique, humain, reglementaire, financier, operationnel',
  probabilite   TINYINT NOT NULL DEFAULT 3,
  impact        TINYINT NOT NULL DEFAULT 3,
  mitigation    TEXT,
  CONSTRAINT fk_risque_projet FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE opportunites (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  projet_id     INT NULL COMMENT 'NULL = opportunité type du catalogue',
  libelle       VARCHAR(220) NOT NULL,
  categorie     VARCHAR(80)  NOT NULL,
  potentiel     TINYINT NOT NULL DEFAULT 3,
  description   TEXT,
  CONSTRAINT fk_opp_projet FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE scenarios (
  id                 INT AUTO_INCREMENT PRIMARY KEY,
  projet_id          INT NOT NULL,
  type_scenario      ENUM('bas','median','haut') NOT NULL,
  ca_3ans_k          DECIMAL(12,2) NOT NULL DEFAULT 0,
  resultat_3ans_k    DECIMAL(12,2) NOT NULL DEFAULT 0,
  roi_pct            DECIMAL(8,2)  NOT NULL DEFAULT 0,
  hypotheses         TEXT,
  UNIQUE KEY uq_scen (projet_id, type_scenario),
  CONSTRAINT fk_scen_projet FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE versions (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  projet_id     INT NOT NULL,
  source        VARCHAR(20) NOT NULL DEFAULT 'user' COMMENT 'user, ia, system',
  label         VARCHAR(120),
  snapshot_json LONGTEXT NOT NULL,
  created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_ver_projet FOREIGN KEY (projet_id) REFERENCES projets(id) ON DELETE CASCADE
) ENGINE=InnoDB;
