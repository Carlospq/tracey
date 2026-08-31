
/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
DROP TABLE IF EXISTS `analysislevels`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `analysislevels` (
  `analysisLevel_id` int NOT NULL AUTO_INCREMENT,
  `name` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `comments` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `level` int NOT NULL DEFAULT '0',
  PRIMARY KEY (`analysisLevel_id`),
  UNIQUE KEY `level` (`level`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `associatedsequences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `associatedsequences` (
  `associatedSequence_id` int NOT NULL AUTO_INCREMENT,
  `gi` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `shortname` varchar(50) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '',
  `sequence` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `active` tinyint NOT NULL DEFAULT '0',
  `comments` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `multi_gi` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `sp` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `changeLog` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `taxonomy_id` int DEFAULT '-1',
  `private` tinyint unsigned NOT NULL DEFAULT '1',
  `aliases` text CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `domainGroup_id` int NOT NULL DEFAULT '0',
  `proteinLayoutGroup_id` int DEFAULT '0',
  PRIMARY KEY (`associatedSequence_id`),
  KEY `as_dg` (`domainGroup_id`),
  KEY `as_ta` (`taxonomy_id`),
  CONSTRAINT `as_dg` FOREIGN KEY (`domainGroup_id`) REFERENCES `domaingroups` (`domainGroup_id`) ON DELETE CASCADE,
  CONSTRAINT `as_ta` FOREIGN KEY (`taxonomy_id`) REFERENCES `taxonomies` (`taxonomy_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=182 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=381 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `auth_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user` (
  `id` int NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `email` varchar(254) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`)
) ENGINE=InnoDB AUTO_INCREMENT=77 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `auth_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_groups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_groups_user_id_group_id_94350c0c_uniq` (`user_id`,`group_id`),
  KEY `auth_user_groups_group_id_97559544_fk_auth_group_id` (`group_id`),
  CONSTRAINT `auth_user_groups_group_id_97559544_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `auth_user_groups_user_id_6a12ed8b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `auth_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_user_user_permissions` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_user_user_permissions_user_id_permission_id_14a6b632_uniq` (`user_id`,`permission_id`),
  KEY `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_user_user_permi_permission_id_1fbb5f2c_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_user_user_permissions_user_id_a95ead1b_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=381 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `captcha_captchastore`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `captcha_captchastore` (
  `id` int NOT NULL AUTO_INCREMENT,
  `challenge` varchar(32) NOT NULL,
  `response` varchar(32) NOT NULL,
  `hashkey` varchar(40) NOT NULL,
  `expiration` datetime(6) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `hashkey` (`hashkey`)
) ENGINE=InnoDB AUTO_INCREMENT=65 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` int NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_auth_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_auth_user_id` FOREIGN KEY (`user_id`) REFERENCES `auth_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=96 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=96 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `domainchild`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `domainchild` (
  `domainGroupName` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci NOT NULL,
  `domainGroup_id` int NOT NULL DEFAULT '0',
  `MotifLineage` varchar(50) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT NULL,
  `domainGroupParent_id` varchar(100) CHARACTER SET utf8mb3 COLLATE utf8mb3_general_ci DEFAULT '-1',
  `analysisLevel` int NOT NULL DEFAULT '0'
) ENGINE=InnoDB DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `domaingroups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `domaingroups` (
  `domainGroup_id` int NOT NULL AUTO_INCREMENT,
  `domainGroupName` varchar(50) NOT NULL,
  `domainGroupFunctionalName` varchar(50) DEFAULT NULL,
  `domainGroupShortname` tinytext,
  `domain_id` int NOT NULL,
  `domainGroupComments` longtext,
  `domainGroupParent_id` varchar(100) DEFAULT '-1',
  `domainGroupLength` int NOT NULL DEFAULT '0',
  `analysisLevel` int NOT NULL DEFAULT '0',
  `appendixName` text,
  `mappingString` longtext NOT NULL,
  `softCutoff` double NOT NULL DEFAULT '10',
  `strictCutoff` double NOT NULL DEFAULT '10',
  `domainGroupModel_id` int DEFAULT NULL,
  `isAlignable` tinyint(1) DEFAULT '1',
  PRIMARY KEY (`domainGroup_id`),
  KEY `dg_d` (`domain_id`),
  CONSTRAINT `dg_d` FOREIGN KEY (`domain_id`) REFERENCES `domains` (`domain_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1867 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `domains`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `domains` (
  `domain_id` int NOT NULL AUTO_INCREMENT,
  `domainName` varchar(50) NOT NULL,
  `domainComments` longtext,
  `alignment` longtext NOT NULL,
  `alignmentLength` int NOT NULL,
  PRIMARY KEY (`domain_id`)
) ENGINE=InnoDB AUTO_INCREMENT=32 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `falsepositives`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `falsepositives` (
  `falsePositive_id` int unsigned NOT NULL AUTO_INCREMENT,
  `domain_id` int unsigned NOT NULL DEFAULT '0',
  `gi` longtext NOT NULL,
  PRIMARY KEY (`falsePositive_id`)
) ENGINE=MyISAM AUTO_INCREMENT=81 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `genes`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `genes` (
  `gene_id` int NOT NULL AUTO_INCREMENT,
  `ncbiGene_id` varchar(10) NOT NULL,
  PRIMARY KEY (`gene_id`)
) ENGINE=InnoDB AUTO_INCREMENT=407416 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `genomesource`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `genomesource` (
  `genomeSource_id` int NOT NULL AUTO_INCREMENT,
  `taxonomy_id` int NOT NULL,
  `ftpLink` text,
  `wwwLink` text,
  `sequenceType` text NOT NULL,
  `version` text NOT NULL,
  `timeCreated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `timeLastModified` timestamp NOT NULL DEFAULT '0000-00-00 00:00:00',
  `xmlParameter` text NOT NULL,
  `sourceDatabase` text NOT NULL,
  PRIMARY KEY (`genomeSource_id`),
  KEY `fk1` (`taxonomy_id`),
  CONSTRAINT `fk1` FOREIGN KEY (`taxonomy_id`) REFERENCES `taxonomies` (`taxonomy_id`)
) ENGINE=InnoDB AUTO_INCREMENT=481 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `goldstatus`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `goldstatus` (
  `goldStamp` varchar(10) NOT NULL,
  `ncbi_taxonomy_id` int NOT NULL,
  `projectstatus` varchar(25) NOT NULL,
  `sequencingstatus` varchar(25) NOT NULL,
  PRIMARY KEY (`goldStamp`),
  KEY `ncbi_taxonomy` (`ncbi_taxonomy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `inserterrors`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `inserterrors` (
  `insertError_id` int NOT NULL AUTO_INCREMENT,
  `motif_id` int NOT NULL DEFAULT '0',
  `startposition` int NOT NULL DEFAULT '-1',
  `stopposition` int NOT NULL DEFAULT '-1',
  PRIMARY KEY (`insertError_id`),
  KEY `ie_md` (`motif_id`),
  CONSTRAINT `ie_md` FOREIGN KEY (`motif_id`) REFERENCES `motifs` (`motif_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1082880 DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `layout_protlayoutgroup`;
/*!50001 DROP VIEW IF EXISTS `layout_protlayoutgroup`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `layout_protlayoutgroup` AS SELECT 
 1 AS `layout_id`,
 1 AS `layoutComments`,
 1 AS `proteinLayoutGroup_id`,
 1 AS `sequence_id`,
 1 AS `layoutRank`,
 1 AS `layoutStatus`,
 1 AS `layoutString`,
 1 AS `proteinLayoutGroupName`,
 1 AS `proteinLayoutGroupFunctionalName`,
 1 AS `proteinLayoutGroupShortname`,
 1 AS `proteinLayout_id`,
 1 AS `proteinLayoutGroupComments`,
 1 AS `proteinLayoutGroupParent_id`,
 1 AS `proteinLayoutGroupLength`,
 1 AS `analysisLevel`,
 1 AS `appendixName`,
 1 AS `mappingString`*/;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `layouts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `layouts` (
  `layout_id` int NOT NULL AUTO_INCREMENT,
  `layoutComments` longtext,
  `proteinLayoutGroup_id` int NOT NULL,
  `sequence_id` int NOT NULL,
  `layoutRank` int NOT NULL DEFAULT '1000000',
  `layoutStatus` text NOT NULL,
  `layoutString` longtext NOT NULL,
  PRIMARY KEY (`layout_id`),
  UNIQUE KEY `seq_id` (`sequence_id`),
  KEY `l_seq` (`sequence_id`),
  KEY `l_plg` (`proteinLayoutGroup_id`),
  CONSTRAINT `l_plg` FOREIGN KEY (`proteinLayoutGroup_id`) REFERENCES `proteinlayoutgroups` (`proteinLayoutGroup_id`) ON DELETE CASCADE,
  CONSTRAINT `l_seq` FOREIGN KEY (`sequence_id`) REFERENCES `sequences` (`sequence_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=334848 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `methods`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `methods` (
  `method_id` int NOT NULL AUTO_INCREMENT,
  `domainGroup_id` int NOT NULL,
  `input` longtext,
  `type` mediumtext NOT NULL,
  `parameter` text,
  PRIMARY KEY (`method_id`)
) ENGINE=InnoDB AUTO_INCREMENT=1709 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `mot_domgr`;
/*!50001 DROP VIEW IF EXISTS `mot_domgr`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `mot_domgr` AS SELECT 
 1 AS `sequence_id`,
 1 AS `motifname`,
 1 AS `startposition`,
 1 AS `stopposition`,
 1 AS `motifComments`,
 1 AS `domainGroup_id`,
 1 AS `motif_id`,
 1 AS `gaps`,
 1 AS `active`,
 1 AS `method_id`,
 1 AS `asciiOutput`,
 1 AS `motifRank`,
 1 AS `binaryOutput`,
 1 AS `domainGroupName`,
 1 AS `domainGroupFunctionalName`,
 1 AS `domainGroupParent_id`,
 1 AS `domainGroupShortname`,
 1 AS `domainGroupLength`,
 1 AS `domain_id`*/;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `motifs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `motifs` (
  `sequence_id` int NOT NULL DEFAULT '0',
  `motifname` tinytext CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `startposition` int NOT NULL DEFAULT '-1',
  `stopposition` int NOT NULL DEFAULT '-1',
  `motifComments` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `domainGroup_id` int NOT NULL DEFAULT '0',
  `motif_id` int NOT NULL AUTO_INCREMENT,
  `gaps` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `active` tinyint NOT NULL DEFAULT '1',
  `method_id` int NOT NULL DEFAULT '0',
  `motifRank` int DEFAULT '1000000',
  `asciiOutput` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `binaryOutput` mediumblob,
  PRIMARY KEY (`motif_id`),
  KEY `md_sd` (`sequence_id`),
  KEY `md_dg` (`domainGroup_id`),
  KEY `md_meth` (`method_id`),
  CONSTRAINT `md_dg` FOREIGN KEY (`domainGroup_id`) REFERENCES `domaingroups` (`domainGroup_id`) ON DELETE CASCADE,
  CONSTRAINT `md_meth` FOREIGN KEY (`method_id`) REFERENCES `methods` (`method_id`),
  CONSTRAINT `md_sd` FOREIGN KEY (`sequence_id`) REFERENCES `sequences` (`sequence_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=525398 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `ncbi_taxonomy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ncbi_taxonomy` (
  `rank` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `scientificName` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `division` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `commonName` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `genus` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `species` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `subspecies` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `ncbi_Taxonomy_id` int NOT NULL DEFAULT '0',
  `nucNumber` int DEFAULT '0',
  `estNumber` int DEFAULT '0',
  `protNumber` int NOT NULL DEFAULT '0',
  `structNumber` int DEFAULT '0',
  `genomeNumber` int DEFAULT '0',
  `geneNumber` int DEFAULT '0',
  `active` tinyint(1) NOT NULL DEFAULT '0',
  `lastUpdate` date DEFAULT '1965-02-08',
  `class` text CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `parent_id` int NOT NULL,
  PRIMARY KEY (`ncbi_Taxonomy_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `ncbi_taxonomysynonyms`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `ncbi_taxonomysynonyms` (
  `name` text NOT NULL,
  `NCBI_TaxonomySynonyms_id` int unsigned NOT NULL AUTO_INCREMENT,
  `NCBI_Taxonomy_id` int NOT NULL,
  `class` text,
  PRIMARY KEY (`NCBI_TaxonomySynonyms_id`),
  KEY `taxsyn_tax` (`NCBI_Taxonomy_id`),
  CONSTRAINT `taxsyn_tax` FOREIGN KEY (`NCBI_Taxonomy_id`) REFERENCES `ncbi_taxonomy` (`ncbi_Taxonomy_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=49487 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `p2dmapping`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `p2dmapping` (
  `p2dMapping_id` int NOT NULL AUTO_INCREMENT,
  `domainGroup_id` int NOT NULL,
  `proteinLayoutGroup_id` int NOT NULL,
  `position` int NOT NULL DEFAULT '-1',
  PRIMARY KEY (`p2dMapping_id`),
  UNIQUE KEY `plg_position` (`proteinLayoutGroup_id`,`position`),
  KEY `p2d_dg` (`domainGroup_id`),
  CONSTRAINT `p2d_dg` FOREIGN KEY (`domainGroup_id`) REFERENCES `domaingroups` (`domainGroup_id`) ON DELETE CASCADE,
  CONSTRAINT `p2d_plg` FOREIGN KEY (`proteinLayoutGroup_id`) REFERENCES `proteinlayoutgroups` (`proteinLayoutGroup_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2209 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `proteinlayoutgroups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `proteinlayoutgroups` (
  `proteinLayoutGroup_id` int NOT NULL AUTO_INCREMENT,
  `proteinLayoutGroupName` varchar(50) NOT NULL,
  `proteinLayoutGroupFunctionalName` varchar(50) DEFAULT NULL,
  `proteinLayoutGroupShortname` tinytext,
  `proteinLayout_id` int NOT NULL,
  `proteinLayoutGroupComments` longtext,
  `proteinLayoutGroupParent_id` int DEFAULT '-1',
  `proteinLayoutGroupLength` int NOT NULL DEFAULT '0',
  `analysisLevel` int NOT NULL DEFAULT '0',
  `appendixName` text,
  `mappingString` longtext NOT NULL,
  PRIMARY KEY (`proteinLayoutGroup_id`),
  KEY `plg_pl` (`proteinLayout_id`),
  CONSTRAINT `plg_pl` FOREIGN KEY (`proteinLayout_id`) REFERENCES `proteinlayouts` (`proteinLayout_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=1083 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `proteinlayouts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `proteinlayouts` (
  `proteinLayout_id` int NOT NULL AUTO_INCREMENT,
  `proteinLayoutName` varchar(50) NOT NULL,
  `proteinLayoutComments` longtext,
  `layout` longtext NOT NULL,
  `layoutLength` int NOT NULL,
  PRIMARY KEY (`proteinLayout_id`)
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `protlayout_protlayoutgroup`;
/*!50001 DROP VIEW IF EXISTS `protlayout_protlayoutgroup`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `protlayout_protlayoutgroup` AS SELECT 
 1 AS `proteinLayout_id`,
 1 AS `proteinLayoutName`,
 1 AS `proteinLayoutComments`,
 1 AS `layout`,
 1 AS `layoutLength`,
 1 AS `proteinLayoutGroup_id`,
 1 AS `proteinLayoutGroupName`,
 1 AS `proteinLayoutGroupFunctionalName`,
 1 AS `proteinLayoutGroupShortname`,
 1 AS `proteinLayoutGroupParent_id`,
 1 AS `proteinLayoutGroupLength`,
 1 AS `analysisLevel`,
 1 AS `appendixName`,
 1 AS `mappingString`*/;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `secondarydomainstructures`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `secondarydomainstructures` (
  `secondaryDomainStructure_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `comments` longtext,
  `dssp` longtext NOT NULL,
  `domainGroup_id` int NOT NULL,
  PRIMARY KEY (`secondaryDomainStructure_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `secondaryproteinlayouts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `secondaryproteinlayouts` (
  `secondaryProteinLayout_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `comments` longtext,
  `dssp` longtext NOT NULL,
  `proteinLayoutGroup_id` int NOT NULL,
  PRIMARY KEY (`secondaryProteinLayout_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `seq_lay`;
/*!50001 DROP VIEW IF EXISTS `seq_lay`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `seq_lay` AS SELECT 
 1 AS `sequence_id`,
 1 AS `foreignAnnotation`,
 1 AS `sequenceShortname`,
 1 AS `annotation`,
 1 AS `sequence`,
 1 AS `sequenceStatus`,
 1 AS `sequenceComments`,
 1 AS `dbxref`,
 1 AS `changeLog`,
 1 AS `taxonomy_id`,
 1 AS `private`,
 1 AS `aliases`,
 1 AS `sourceDatabase`,
 1 AS `replacedBy`,
 1 AS `sequenceType`,
 1 AS `gene_id`,
 1 AS `layout_id`,
 1 AS `layoutComments`,
 1 AS `proteinLayoutGroup_id`,
 1 AS `layoutRank`,
 1 AS `layoutStatus`,
 1 AS `layoutString`*/;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `seq_mot`;
/*!50001 DROP VIEW IF EXISTS `seq_mot`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `seq_mot` AS SELECT 
 1 AS `sequence_id`,
 1 AS `foreignAnnotation`,
 1 AS `sequenceShortname`,
 1 AS `annotation`,
 1 AS `sequence`,
 1 AS `sequenceStatus`,
 1 AS `sequenceComments`,
 1 AS `dbxref`,
 1 AS `changeLog`,
 1 AS `taxonomy_id`,
 1 AS `private`,
 1 AS `aliases`,
 1 AS `sourceDatabase`,
 1 AS `replacedBy`,
 1 AS `sequenceType`,
 1 AS `gene_id`,
 1 AS `motifname`,
 1 AS `startposition`,
 1 AS `stopposition`,
 1 AS `domainGroup_id`,
 1 AS `motif_id`,
 1 AS `gaps`,
 1 AS `active`,
 1 AS `method_id`,
 1 AS `motifRank`,
 1 AS `asciiOutput`,
 1 AS `binaryOutput`,
 1 AS `motifComments`*/;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `seq_tax`;
/*!50001 DROP VIEW IF EXISTS `seq_tax`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `seq_tax` AS SELECT 
 1 AS `sequence_id`,
 1 AS `foreignAnnotation`,
 1 AS `sequenceShortname`,
 1 AS `annotation`,
 1 AS `sequence`,
 1 AS `sequenceStatus`,
 1 AS `sequenceComments`,
 1 AS `dbxref`,
 1 AS `changeLog`,
 1 AS `taxonomy_id`,
 1 AS `private`,
 1 AS `aliases`,
 1 AS `sourceDatabase`,
 1 AS `replacedBy`,
 1 AS `sequenceType`,
 1 AS `gene_id`,
 1 AS `scientificName`,
 1 AS `commonName`,
 1 AS `taxonomyParent_id`,
 1 AS `taxonomyComments`,
 1 AS `taxonomyStatus`,
 1 AS `taxonomyRank`,
 1 AS `taxonomyShortname`*/;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `seq_vermot`;
/*!50001 DROP VIEW IF EXISTS `seq_vermot`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `seq_vermot` AS SELECT 
 1 AS `sequence_id`,
 1 AS `foreignAnnotation`,
 1 AS `sequenceShortname`,
 1 AS `annotation`,
 1 AS `sequence`,
 1 AS `sequenceStatus`,
 1 AS `sequenceComments`,
 1 AS `dbxref`,
 1 AS `changeLog`,
 1 AS `taxonomy_id`,
 1 AS `private`,
 1 AS `aliases`,
 1 AS `sourceDatabase`,
 1 AS `replacedBy`,
 1 AS `sequenceType`,
 1 AS `gene_id`,
 1 AS `motifname`,
 1 AS `startposition`,
 1 AS `stopposition`,
 1 AS `domainGroup_id`,
 1 AS `verifyMotif_id`,
 1 AS `gaps`,
 1 AS `active`,
 1 AS `verifyMotifRank`,
 1 AS `method_id`,
 1 AS `asciiOutput`,
 1 AS `binaryOutput`,
 1 AS `verifyMotifComments`*/;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `sequences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `sequences` (
  `sequence_id` int NOT NULL AUTO_INCREMENT,
  `foreignAnnotation` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `sequenceShortname` varchar(50) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `annotation` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `sequence` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `sequenceStatus` text CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `sequenceComments` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `dbxref` varchar(25) NOT NULL,
  `changeLog` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `taxonomy_id` int DEFAULT '-1',
  `private` tinyint unsigned NOT NULL DEFAULT '1',
  `aliases` text CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `sourceDatabase` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `replacedBy` int NOT NULL DEFAULT '-1',
  `sequenceType` varchar(25) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT 'Unknown',
  `gene_id` int NOT NULL DEFAULT '-1',
  PRIMARY KEY (`sequence_id`),
  UNIQUE KEY `sourceDB_dbxref` (`dbxref`,`sourceDatabase`(25)),
  KEY `seq_gene` (`gene_id`),
  KEY `seq_tax` (`taxonomy_id`),
  CONSTRAINT `seq_gene` FOREIGN KEY (`gene_id`) REFERENCES `genes` (`gene_id`) ON DELETE CASCADE,
  CONSTRAINT `seq_tax` FOREIGN KEY (`taxonomy_id`) REFERENCES `taxonomies` (`taxonomy_id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=454455 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `species`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `species` (
  `species_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL DEFAULT '',
  `comments` longtext,
  `parent_id` int DEFAULT NULL,
  `taxonomy_id` int unsigned NOT NULL DEFAULT '0',
  `shortname` text,
  PRIMARY KEY (`species_id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `synonymgroups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `synonymgroups` (
  `id` int NOT NULL AUTO_INCREMENT,
  `id1` int NOT NULL DEFAULT '0',
  `id2` int NOT NULL DEFAULT '0',
  `comments` longtext,
  PRIMARY KEY (`id`)
) ENGINE=MyISAM DEFAULT CHARSET=latin1;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `taxonomies`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `taxonomies` (
  `taxonomy_id` int NOT NULL AUTO_INCREMENT,
  `commonName` text CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `scientificName` text CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `taxonomyComments` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `taxonomyParent_id` int NOT NULL DEFAULT '-1',
  `analysisLevel` varchar(15) CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL DEFAULT '-1',
  `taxonomyRank` text CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `taxonomyShortname` tinytext CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `ncbi_Taxonomy_id` int NOT NULL DEFAULT '0',
  `taxonomyStatus` text CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  PRIMARY KEY (`taxonomy_id`),
  KEY `tax_NTax` (`ncbi_Taxonomy_id`)
) ENGINE=InnoDB AUTO_INCREMENT=27331 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `tertiarydomainstructures`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tertiarydomainstructures` (
  `tertiaryDomainStructure_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `comments` longtext NOT NULL,
  `pdb` longtext NOT NULL,
  `domainGroup_id` int DEFAULT NULL,
  PRIMARY KEY (`tertiaryDomainStructure_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `tertiaryproteinlayouts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `tertiaryproteinlayouts` (
  `tertiaryProteinLayout_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(50) NOT NULL,
  `comments` longtext,
  `pdb` longtext NOT NULL,
  `proteinLayoutGroup_id` int NOT NULL,
  PRIMARY KEY (`tertiaryProteinLayout_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `updatetask2sequences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `updatetask2sequences` (
  `updateTask2sequences_id` int unsigned NOT NULL AUTO_INCREMENT,
  `sequence_id` int NOT NULL,
  `new_sequence_id` int NOT NULL,
  `update_task_id` int unsigned NOT NULL,
  PRIMARY KEY (`updateTask2sequences_id`),
  KEY `fk4` (`update_task_id`),
  KEY `fk2` (`sequence_id`),
  KEY `fk3` (`new_sequence_id`),
  CONSTRAINT `fk2` FOREIGN KEY (`sequence_id`) REFERENCES `sequences` (`sequence_id`),
  CONSTRAINT `fk3` FOREIGN KEY (`new_sequence_id`) REFERENCES `sequences` (`sequence_id`),
  CONSTRAINT `fk4` FOREIGN KEY (`update_task_id`) REFERENCES `updatetasks` (`updateTask_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `updatetask2user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `updatetask2user` (
  `updatetask2user_id` int unsigned NOT NULL AUTO_INCREMENT,
  `updatetask_id` int unsigned NOT NULL,
  `user_id` int unsigned NOT NULL,
  PRIMARY KEY (`updatetask2user_id`),
  KEY `fk_updatetasks` (`updatetask_id`),
  KEY `fk_user` (`user_id`),
  CONSTRAINT `fk_updatetasks` FOREIGN KEY (`updatetask_id`) REFERENCES `updatetasks` (`updateTask_id`),
  CONSTRAINT `fk_user` FOREIGN KEY (`user_id`) REFERENCES `administration`.`user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `updatetasks`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `updatetasks` (
  `updateTask_id` int unsigned NOT NULL AUTO_INCREMENT,
  `updateTaskType` varchar(25) NOT NULL,
  `affectedTable` varchar(25) NOT NULL,
  `updateTaskComments` bigint DEFAULT NULL,
  `taskUpdateTime` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`updateTask_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user` (
  `user_id` int unsigned NOT NULL AUTO_INCREMENT,
  `username` varchar(60) NOT NULL DEFAULT '',
  `password` varchar(60) NOT NULL DEFAULT '',
  `rights` varchar(60) NOT NULL DEFAULT '',
  PRIMARY KEY (`user_id`)
) ENGINE=MyISAM AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `verifylayouts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `verifylayouts` (
  `verifyLayout_id` int NOT NULL AUTO_INCREMENT,
  PRIMARY KEY (`verifyLayout_id`)
) ENGINE=MyISAM DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `verifymotifs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `verifymotifs` (
  `sequence_id` int NOT NULL DEFAULT '0',
  `motifname` tinytext CHARACTER SET latin1 COLLATE latin1_swedish_ci NOT NULL,
  `startposition` int NOT NULL DEFAULT '-1',
  `stopposition` int NOT NULL DEFAULT '-1',
  `verifyMotifComments` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `domainGroup_id` int NOT NULL DEFAULT '-1',
  `verifyMotif_id` int NOT NULL AUTO_INCREMENT,
  `gaps` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `active` tinyint NOT NULL DEFAULT '0',
  `method_id` int NOT NULL,
  `verifyMotifRank` int DEFAULT '0',
  `asciiOutput` longtext CHARACTER SET latin1 COLLATE latin1_swedish_ci,
  `binaryOutput` mediumblob,
  PRIMARY KEY (`verifyMotif_id`),
  KEY `vm_seq` (`sequence_id`),
  KEY `mv_dg` (`domainGroup_id`),
  KEY `vmd_meth` (`method_id`),
  CONSTRAINT `mv_dg` FOREIGN KEY (`domainGroup_id`) REFERENCES `domaingroups` (`domainGroup_id`) ON DELETE CASCADE,
  CONSTRAINT `vm_seq` FOREIGN KEY (`sequence_id`) REFERENCES `sequences` (`sequence_id`) ON DELETE CASCADE,
  CONSTRAINT `vmd_meth` FOREIGN KEY (`method_id`) REFERENCES `methods` (`method_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6186169 DEFAULT CHARSET=utf8mb3;
/*!40101 SET character_set_client = @saved_cs_client */;
DROP TABLE IF EXISTS `vermot_domgr`;
/*!50001 DROP VIEW IF EXISTS `vermot_domgr`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vermot_domgr` AS SELECT 
 1 AS `sequence_id`,
 1 AS `motifname`,
 1 AS `startposition`,
 1 AS `stopposition`,
 1 AS `verifyMotifComments`,
 1 AS `domainGroup_id`,
 1 AS `verifyMotif_id`,
 1 AS `gaps`,
 1 AS `active`,
 1 AS `method_id`,
 1 AS `verifyMotifRank`,
 1 AS `asciiOutput`,
 1 AS `binaryOutput`,
 1 AS `domainGroupName`,
 1 AS `domainGroupFunctionalName`,
 1 AS `domainGroupParent_id`,
 1 AS `domainGroupShortname`,
 1 AS `domainGroupLength`,
 1 AS `domainGroupComments`*/;
SET character_set_client = @saved_cs_client;
DROP TABLE IF EXISTS `vermot_tax`;
/*!50001 DROP VIEW IF EXISTS `vermot_tax`*/;
SET @saved_cs_client     = @@character_set_client;
/*!50503 SET character_set_client = utf8mb4 */;
/*!50001 CREATE VIEW `vermot_tax` AS SELECT 
 1 AS `sequence_id`,
 1 AS `motifname`,
 1 AS `startposition`,
 1 AS `stopposition`,
 1 AS `verifyMotifComments`,
 1 AS `domainGroup_id`,
 1 AS `verifyMotif_id`,
 1 AS `gaps`,
 1 AS `active`,
 1 AS `method_id`,
 1 AS `verifyMotifRank`,
 1 AS `asciiOutput`,
 1 AS `binaryOutput`,
 1 AS `taxonomy_id`,
 1 AS `scientificname`,
 1 AS `commonName`,
 1 AS `taxonomyParent_id`,
 1 AS `taxonomyComments`,
 1 AS `taxonomyStatus`,
 1 AS `taxonomyRank`,
 1 AS `taxonomyShortname`*/;
SET character_set_client = @saved_cs_client;
/*!50001 DROP VIEW IF EXISTS `layout_protlayoutgroup`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 SQL SECURITY DEFINER */
/*!50001 VIEW `layout_protlayoutgroup` AS select `l`.`layout_id` AS `layout_id`,`l`.`layoutComments` AS `layoutComments`,`l`.`proteinLayoutGroup_id` AS `proteinLayoutGroup_id`,`l`.`sequence_id` AS `sequence_id`,`l`.`layoutRank` AS `layoutRank`,`l`.`layoutStatus` AS `layoutStatus`,`l`.`layoutString` AS `layoutString`,`plg`.`proteinLayoutGroupName` AS `proteinLayoutGroupName`,`plg`.`proteinLayoutGroupFunctionalName` AS `proteinLayoutGroupFunctionalName`,`plg`.`proteinLayoutGroupShortname` AS `proteinLayoutGroupShortname`,`plg`.`proteinLayout_id` AS `proteinLayout_id`,`plg`.`proteinLayoutGroupComments` AS `proteinLayoutGroupComments`,`plg`.`proteinLayoutGroupParent_id` AS `proteinLayoutGroupParent_id`,`plg`.`proteinLayoutGroupLength` AS `proteinLayoutGroupLength`,`plg`.`analysisLevel` AS `analysisLevel`,`plg`.`appendixName` AS `appendixName`,`plg`.`mappingString` AS `mappingString` from (`layouts` `l` join `proteinlayoutgroups` `plg` on((`l`.`proteinLayoutGroup_id` = `plg`.`proteinLayoutGroup_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `mot_domgr`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 SQL SECURITY DEFINER */
/*!50001 VIEW `mot_domgr` AS select `m`.`sequence_id` AS `sequence_id`,`m`.`motifname` AS `motifname`,`m`.`startposition` AS `startposition`,`m`.`stopposition` AS `stopposition`,`m`.`motifComments` AS `motifComments`,`m`.`domainGroup_id` AS `domainGroup_id`,`m`.`motif_id` AS `motif_id`,`m`.`gaps` AS `gaps`,`m`.`active` AS `active`,`m`.`method_id` AS `method_id`,`m`.`asciiOutput` AS `asciiOutput`,`m`.`motifRank` AS `motifRank`,`m`.`binaryOutput` AS `binaryOutput`,`dg`.`domainGroupName` AS `domainGroupName`,`dg`.`domainGroupFunctionalName` AS `domainGroupFunctionalName`,`dg`.`domainGroupParent_id` AS `domainGroupParent_id`,`dg`.`domainGroupShortname` AS `domainGroupShortname`,`dg`.`domainGroupLength` AS `domainGroupLength`,`dg`.`domain_id` AS `domain_id` from (`motifs` `m` join `domaingroups` `dg` on((`m`.`domainGroup_id` = `dg`.`domainGroup_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `protlayout_protlayoutgroup`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 SQL SECURITY DEFINER */
/*!50001 VIEW `protlayout_protlayoutgroup` AS select `pl`.`proteinLayout_id` AS `proteinLayout_id`,`pl`.`proteinLayoutName` AS `proteinLayoutName`,`pl`.`proteinLayoutComments` AS `proteinLayoutComments`,`pl`.`layout` AS `layout`,`pl`.`layoutLength` AS `layoutLength`,`plg`.`proteinLayoutGroup_id` AS `proteinLayoutGroup_id`,`plg`.`proteinLayoutGroupName` AS `proteinLayoutGroupName`,`plg`.`proteinLayoutGroupFunctionalName` AS `proteinLayoutGroupFunctionalName`,`plg`.`proteinLayoutGroupShortname` AS `proteinLayoutGroupShortname`,`plg`.`proteinLayoutGroupParent_id` AS `proteinLayoutGroupParent_id`,`plg`.`proteinLayoutGroupLength` AS `proteinLayoutGroupLength`,`plg`.`analysisLevel` AS `analysisLevel`,`plg`.`appendixName` AS `appendixName`,`plg`.`mappingString` AS `mappingString` from (`proteinlayouts` `pl` join `proteinlayoutgroups` `plg` on((`pl`.`proteinLayout_id` = `plg`.`proteinLayout_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `seq_lay`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 SQL SECURITY DEFINER */
/*!50001 VIEW `seq_lay` AS select `s`.`sequence_id` AS `sequence_id`,`s`.`foreignAnnotation` AS `foreignAnnotation`,`s`.`sequenceShortname` AS `sequenceShortname`,`s`.`annotation` AS `annotation`,`s`.`sequence` AS `sequence`,`s`.`sequenceStatus` AS `sequenceStatus`,`s`.`sequenceComments` AS `sequenceComments`,`s`.`dbxref` AS `dbxref`,`s`.`changeLog` AS `changeLog`,`s`.`taxonomy_id` AS `taxonomy_id`,`s`.`private` AS `private`,`s`.`aliases` AS `aliases`,`s`.`sourceDatabase` AS `sourceDatabase`,`s`.`replacedBy` AS `replacedBy`,`s`.`sequenceType` AS `sequenceType`,`s`.`gene_id` AS `gene_id`,`l`.`layout_id` AS `layout_id`,`l`.`layoutComments` AS `layoutComments`,`l`.`proteinLayoutGroup_id` AS `proteinLayoutGroup_id`,`l`.`layoutRank` AS `layoutRank`,`l`.`layoutStatus` AS `layoutStatus`,`l`.`layoutString` AS `layoutString` from (`sequences` `s` join `layouts` `l` on((`s`.`sequence_id` = `l`.`sequence_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `seq_mot`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 SQL SECURITY DEFINER */
/*!50001 VIEW `seq_mot` AS select `s`.`sequence_id` AS `sequence_id`,`s`.`foreignAnnotation` AS `foreignAnnotation`,`s`.`sequenceShortname` AS `sequenceShortname`,`s`.`annotation` AS `annotation`,`s`.`sequence` AS `sequence`,`s`.`sequenceStatus` AS `sequenceStatus`,`s`.`sequenceComments` AS `sequenceComments`,`s`.`dbxref` AS `dbxref`,`s`.`changeLog` AS `changeLog`,`s`.`taxonomy_id` AS `taxonomy_id`,`s`.`private` AS `private`,`s`.`aliases` AS `aliases`,`s`.`sourceDatabase` AS `sourceDatabase`,`s`.`replacedBy` AS `replacedBy`,`s`.`sequenceType` AS `sequenceType`,`s`.`gene_id` AS `gene_id`,`m`.`motifname` AS `motifname`,`m`.`startposition` AS `startposition`,`m`.`stopposition` AS `stopposition`,`m`.`domainGroup_id` AS `domainGroup_id`,`m`.`motif_id` AS `motif_id`,`m`.`gaps` AS `gaps`,`m`.`active` AS `active`,`m`.`method_id` AS `method_id`,`m`.`motifRank` AS `motifRank`,`m`.`asciiOutput` AS `asciiOutput`,`m`.`binaryOutput` AS `binaryOutput`,`m`.`motifComments` AS `motifComments` from (`sequences` `s` join `motifs` `m` on((`s`.`sequence_id` = `m`.`sequence_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `seq_tax`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 SQL SECURITY DEFINER */
/*!50001 VIEW `seq_tax` AS select `s`.`sequence_id` AS `sequence_id`,`s`.`foreignAnnotation` AS `foreignAnnotation`,`s`.`sequenceShortname` AS `sequenceShortname`,`s`.`annotation` AS `annotation`,`s`.`sequence` AS `sequence`,`s`.`sequenceStatus` AS `sequenceStatus`,`s`.`sequenceComments` AS `sequenceComments`,`s`.`dbxref` AS `dbxref`,`s`.`changeLog` AS `changeLog`,`s`.`taxonomy_id` AS `taxonomy_id`,`s`.`private` AS `private`,`s`.`aliases` AS `aliases`,`s`.`sourceDatabase` AS `sourceDatabase`,`s`.`replacedBy` AS `replacedBy`,`s`.`sequenceType` AS `sequenceType`,`s`.`gene_id` AS `gene_id`,`t`.`scientificName` AS `scientificName`,`t`.`commonName` AS `commonName`,`t`.`taxonomyParent_id` AS `taxonomyParent_id`,`t`.`taxonomyComments` AS `taxonomyComments`,`t`.`taxonomyStatus` AS `taxonomyStatus`,`t`.`taxonomyRank` AS `taxonomyRank`,`t`.`taxonomyShortname` AS `taxonomyShortname` from (`sequences` `s` join `taxonomies` `t` on((`s`.`taxonomy_id` = `t`.`taxonomy_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `seq_vermot`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 SQL SECURITY DEFINER */
/*!50001 VIEW `seq_vermot` AS select `s`.`sequence_id` AS `sequence_id`,`s`.`foreignAnnotation` AS `foreignAnnotation`,`s`.`sequenceShortname` AS `sequenceShortname`,`s`.`annotation` AS `annotation`,`s`.`sequence` AS `sequence`,`s`.`sequenceStatus` AS `sequenceStatus`,`s`.`sequenceComments` AS `sequenceComments`,`s`.`dbxref` AS `dbxref`,`s`.`changeLog` AS `changeLog`,`s`.`taxonomy_id` AS `taxonomy_id`,`s`.`private` AS `private`,`s`.`aliases` AS `aliases`,`s`.`sourceDatabase` AS `sourceDatabase`,`s`.`replacedBy` AS `replacedBy`,`s`.`sequenceType` AS `sequenceType`,`s`.`gene_id` AS `gene_id`,`vm`.`motifname` AS `motifname`,`vm`.`startposition` AS `startposition`,`vm`.`stopposition` AS `stopposition`,`vm`.`domainGroup_id` AS `domainGroup_id`,`vm`.`verifyMotif_id` AS `verifyMotif_id`,`vm`.`gaps` AS `gaps`,`vm`.`active` AS `active`,`vm`.`verifyMotifRank` AS `verifyMotifRank`,`vm`.`method_id` AS `method_id`,`vm`.`asciiOutput` AS `asciiOutput`,`vm`.`binaryOutput` AS `binaryOutput`,`vm`.`verifyMotifComments` AS `verifyMotifComments` from (`sequences` `s` join `verifymotifs` `vm` on((`s`.`sequence_id` = `vm`.`sequence_id`))) */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `vermot_domgr`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 SQL SECURITY DEFINER */
/*!50001 VIEW `vermot_domgr` AS select 1 AS `sequence_id`,1 AS `motifname`,1 AS `startposition`,1 AS `stopposition`,1 AS `verifyMotifComments`,1 AS `domainGroup_id`,1 AS `verifyMotif_id`,1 AS `gaps`,1 AS `active`,1 AS `method_id`,1 AS `verifyMotifRank`,1 AS `asciiOutput`,1 AS `binaryOutput`,1 AS `domainGroupName`,1 AS `domainGroupFunctionalName`,1 AS `domainGroupParent_id`,1 AS `domainGroupShortname`,1 AS `domainGroupLength`,1 AS `domainGroupComments` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!50001 DROP VIEW IF EXISTS `vermot_tax`*/;
/*!50001 SET @saved_cs_client          = @@character_set_client */;
/*!50001 SET @saved_cs_results         = @@character_set_results */;
/*!50001 SET @saved_col_connection     = @@collation_connection */;
/*!50001 SET character_set_client      = utf8mb3 */;
/*!50001 SET character_set_results     = utf8mb3 */;
/*!50001 SET collation_connection      = utf8mb3_general_ci */;
/*!50001 CREATE ALGORITHM=UNDEFINED */
/*!50013 SQL SECURITY DEFINER */
/*!50001 VIEW `vermot_tax` AS select 1 AS `sequence_id`,1 AS `motifname`,1 AS `startposition`,1 AS `stopposition`,1 AS `verifyMotifComments`,1 AS `domainGroup_id`,1 AS `verifyMotif_id`,1 AS `gaps`,1 AS `active`,1 AS `method_id`,1 AS `verifyMotifRank`,1 AS `asciiOutput`,1 AS `binaryOutput`,1 AS `taxonomy_id`,1 AS `scientificname`,1 AS `commonName`,1 AS `taxonomyParent_id`,1 AS `taxonomyComments`,1 AS `taxonomyStatus`,1 AS `taxonomyRank`,1 AS `taxonomyShortname` */;
/*!50001 SET character_set_client      = @saved_cs_client */;
/*!50001 SET character_set_results     = @saved_cs_results */;
/*!50001 SET collation_connection      = @saved_col_connection */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

