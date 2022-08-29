import argparse
import os
import subprocess
import sys
import platform

parser = argparse.ArgumentParser()
parser.add_argument(
    'cmd',
    choices=('install', 'reset-db', 'mkdirs', 'check-dirs')
)

if __name__ == '__main__':
    args = parser.parse_args()
    if args.cmd == 'install':
        print("Préparation de l'installation de beassist ...")    
        print("Étape 1/ : Installation des dépendances ...")
        try:
            subprocess.call(['pip', 'install', '-r', 'requirements.txt'])
        except (Exception, ) as e:
            print("Erreur lors de l'installation des dépendances:")
            print(f'{e.__class__.__name__} : {e.args[0]}')
            print("Arrêt du processus d'installation")
            sys.exit()
        else:
            print('Dépendances installées avec succès. Étape 3/ accompli')
        
        print("Étape 2/ : Vérification du fichier de configuration ...")
        if os.path.exists('.env') and os.path.isfile('.env'):
            print("Fichier de configuration déjà existant")
        else:
            try:
                os.rename('.env.exemple', '.env')
            except (FileNotFoundError, ) as e:
                print("Beassit n'a pas retrouvé de fichier de configuration ni de modèle d'exemple")
                print("Arrêt du processus d'installation")
                sys.exit()
            else:
                print("Beassit n'a pas retrouvé de fichier de configuration et en à générer un grâce au modèle")
                print("Pensez à mettre à jour les données dans votre fichier de configuration .env")
        print("Vérification de configuration effectif. Étape 4/ accompli")

        
        print("Étape 3/ : Création des répertoires importants ...")
        try:
            from ut1ls.orm import DOCS_PATH, COMPTA_PATH, FILES_PATH, BACKUP_PATH
        except (ImportError, ) as e:
            print("BéAssist n'à pas pu définir les répertoires utiles depuis le fichier orm")
            sys.exit()
        else:
            for path in (DOCS_PATH, BACKUP_PATH, COMPTA_PATH, FILES_PATH):
                try:
                    os.makedirs(path, exist_ok=True)   
                except (Exception, ) as e:
                    print(f"Erreur lors de la création du répertoire {path}")
                    print(f'{e.__class__.__name__} : {e.args[0]}')
                    print("Arrêt du processus d'installation")
                    sys.exit()
                else:
                    print(f'Répertoire {path} créé !')
            else:
                print("Tous les répertoires necéssaires ont été créés avec succès. Étape 5/ accompli.")
        
        print("Étape 4/ : Mise en place de la base de données ...")
        from ut1ls.orm import db, Admin, Organization, City, Customer,\
            Event, Facture, ListProduction, ListPack, Pack, PackSubTask, SubTask
        
        try:
            db.create_tables((Admin, Organization, City, Customer, Event, Facture,\
                ListProduction, ListPack, Pack, SubTask, PackSubTask))
        except (Exception, ) as e:
            print(f"Erreur lors de la création des tables en base de données")
            print(f'{e.__class__.__name__} : {e.args[0]}')
            print("Arrêt du processus d'installation")
            sys.exit()
        else:
            print("Base de données en place !. Étape 6/ accompli.")
        
        print("Fin de l'installation de beassist !!!")
        print("Configurez votre fichier .env")
        print("Ajoutez votre fichier credentials.json dans le dossier files")
        print("Démarrez votre serveur avec la commande python app.py dans un terminal")
        print("Rendez vous dans votre terminal à l'addresse indiquée")
        
            
            