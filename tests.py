from ut1ls.mailer import Mailer
from ut1ls.orm import Customer, City, Pack, PackSubTask, Facture, SubTask,Task
import unittest
from unittest import TestCase
from requests.sessions import Session
from urllib.parse import urljoin
import peewee as pw


test_db = pw.SqliteDatabase(':memory:')

class MailTest(TestCase):
    def test_mail_sending(self):
        m = Mailer()
        r: dict = m.send_message(
            'tomavorebeka@gmail.com',
            'Message test',
            'Ceci est juste un test',
            ['../beassist/docs/af3b11bc-2022-C.pdf', ]
        )

        self.assertIn('SENT', r.get('labelIds'), "SENT not found in labelsIds")

class CRUDTest(TestCase):
    def setUp(self) -> None:
        test_db.bind([Customer, City, Pack, PackSubTask, Facture, SubTask,Task])
        test_db.connect()
        test_db.create_tables([Customer, City, Pack, PackSubTask, Facture, SubTask,Task])
        self.session = Session()
        self.baseURL = 'http://127.0.0.1:8000'
        

    def tearDown(self) -> None:
        test_db.drop_tables([Customer, City, Pack, PackSubTask, Facture, SubTask,Task])
        test_db.close()

class CustomerTest(CRUDTest):
    def create_customers(self):
        users = [{
            'name': 'Prospect Commercial Régulier',
            'email': 'pdetchenou@gmail.com',
            'phone': '62341626',
            'porte': '213',
            'street': 'Lokossa',
            'appart': '',
            'city': 'Lokossa',
            'province':'Mono',
            'postal': '0324',
            'statut': 'C',
            'is_regulier': 'on',
            'is_prospect': 'on'
        }, {
            'name': 'Prospect Institut Irrégulier',
            'email': 'testeur1@gmail.com',
            'phone': '4301929121',
            'porte': '213',
            'street': 'Av. Montaigne',
            'appart': '83',
            'city': 'Saint-Eustache',
            'province':'Québec',
            'postal': 'QC B3E 2A9',
            'statut': 'I',
            'is_prospect': 'on'
        }, {
            'name': 'Client Résidentiel Régulier',
            'email': '',
            'phone': '4303919271',
            'porte': '213',
            'street': 'Av. Montaigne',
            'appart': '83',
            'city': 'Saint-Eustache',
            'province':'Québec',
            'postal': 'QC B3E 2A9',
            'statut': 'R',
            'is_regulier': 'on',
        }, {
            'name': 'Client Résidentiel Irrégulier',
            'email': '',
            'phone': '',
            'porte': '213',
            'street': 'Bd.. Montaigne',
            'appart': '',
            'city': 'Sainte-Adèle',
            'province':'Québec',
            'postal': 'QC B3E 2A9',
            'statut': 'C',
        }]

        for user in users:
            try:
                self.session.post(urljoin(self.baseURL, '/api/v1/customer/create'), data=user)
            except (Exception, ) as e:
                print(e)
                return False
        return True

    def test_customer_create(self):
        data = {
            'name': 'Enfant des gens',
            'email': 'pdetchenou@gmail.com',
            'phone': '62341626',
            'porte': '213',
            'street': 'Lokossa',
            'appart': '',
            'city': 'Lokossa',
            'province':'Mono',
            'postal': '0324',
            'statut': 'C',
            'is_regulier': 'on',
            'is_prospect': 'on'
        }
        
        r = self.session.post(urljoin(self.baseURL, '/api/v1/customer/create'), data=data)
        r: dict = r.json()
        self.assertEqual(
            r.get('message'),
            f"Utilisateur {data.get('name')} créé avec succès",
            r.get('message')
        )
        c = Customer.get(name = data.get('name'))
        self.assertIsInstance(
            c,
            Customer,
            f"{c} n'est pas un customer"
        )
    
    def test_customer_retrieve(self):
        if self.create_customers():
            r = self.session.get(urljoin(self.baseURL, '/api/v1/customer/1'))
            data : dict = r.json()
            self.assertEqual(data.get('data').get('pk'), 1)
    
    def test_customer_update(self):
        if self.create_customers():
            c : Customer = Customer.get(pk=1)
            nw = {
                    'name': 'Prospect Commercial Irrégulier',
                    'email': 'pdetchenou@gmail.com',
                    'phone': '62341626',
                    'porte': '213',
                    'street': 'Lokossa',
                    'appart': '',
                    'city': 'Lokossa',
                    'province':'Mono',
                    'postal': '0324',
                    'statut': 'C',
                    'is_prospect': 'on'
                }
            
            self.assertEqual(c.name, 'Prospect Commercial Régulier')
            self.assertEqual(c.is_regulier, True)
            r = self.session.post(
                urljoin(self.baseURL, '/api/v1/customer/update/1'),
                data= nw
            )
            data :dict = r.json()
            c : Customer = Customer.get(pk=1)
            self.assertEqual(data.get('data').get('name'), 'Prospect Commercial Irrégulier')
            self.assertEqual(c.is_regulier, False)

    def test_customer_delete(self):
        if self.create_customers():
            c : Customer = Customer.get(pk=3)
            self.assertEqual(c.name, 'Client Résidentiel Régulier')
            self.session.post(urljoin(self.baseURL, '/api/v1/customer/delete/3'))
            with self.assertRaises(pw.DoesNotExist):
                Customer.get(Customer.is_prospect == False & Customer.is_regulier == True)

class PackTest(CRUDTest):
    def test_create_pack(self):
        pass
        #r = self.
if __name__ == '__main__':
    unittest.main()
