import os
import sys
import argparse
import csv
import hashlib as hb
import shutil
import time
from datetime import datetime as dt

import peewee as pw
from dotenv import load_dotenv
from fpdf import FPDF
from fpdf.template import Template
from tabulate import tabulate

ENCODING = sys.getfilesystemencoding()
load_dotenv()


parser = argparse.ArgumentParser()
parser.add_argument(
    "cmd",
    choices=(
        "create-tables",
        "create-dirs",
    ),
)

DOCS_PATH = os.getenv("DOCS_PATH")
COMPTA_PATH = os.getenv("COMPTA_PATH")
BACKUP_PATH = os.getenv("BACKUP_PATH")
FILES_PATH = os.getenv("FILES_PATH")
CSV_PATH = os.getenv("CSV_PATH")


def percent(p, height=False):
    w = 210.00
    h = 297.00

    return (p / 100) * (h if height else w)


db = pw.SqliteDatabase("database.db3")


class BaseModel(pw.Model):
    class Meta:
        database = db


class City(BaseModel):
    pk = pw.IntegerField(primary_key=True)
    name = pw.CharField()

    def serialize(self):
        return {"pk": self.pk, "name": self.name}

    @staticmethod
    def to_csv(filename="./backup/cities.csv"):
        with open(filename, "w", encoding=ENCODING) as f:
            w = csv.DictWriter(
                f,
                fieldnames=[
                    "name",
                ],
                delimiter=";",
            )

            w.writerows(
                [
                    {
                        "name": city.name,
                    }
                    for city in City.select()
                ]
            )

    @staticmethod
    def read_csv(filename="./backup/cities.csv"):
        with open(filename, "r", encoding=ENCODING) as f:
            reader = csv.DictReader(
                f,
                fieldnames=[
                    "name",
                ],
                delimiter=";",
            )

            with db.atomic():
                for city in reader:
                    City.create(**city)

    def __str__(self):
        return f"Ville : {self.name}"

    def __repr__(self) -> str:
        return self.__str__()


class Customer(BaseModel):
    pk = pw.IntegerField(primary_key=True)
    name = pw.CharField()
    porte = pw.IntegerField()
    street = pw.CharField()
    city: City = pw.ForeignKeyField(City, backref="customers")
    appart = pw.IntegerField(null=True)
    joined: dt = pw.DateTimeField(default=dt.now)
    postal = pw.CharField(max_length=12)
    province = pw.CharField(default="Québec")
    email = pw.CharField(null=True)
    phone = pw.CharField(null=True)
    statut = pw.CharField(max_length=1, choices=("I", "C", "R"), default="C")
    is_regulier = pw.BooleanField(default=False)
    is_prospect = pw.BooleanField(default=False)

    @staticmethod
    def lister():
        print(
            tabulate(
                [[cus.pk, cus.name, cus.phone] for cus in Customer.select()],
                headers=["ID", "Nom", "Contact"],
                tablefmt="orgtbl",
            )
        )

    def addresse(self) -> str:
        return (
            f"{self.porte} {self.street} app {self.appart} {self.city.name}"
            if self.appart
            else f"{self.porte} {self.street} {self.city.name}"
        )

    def billet(self) -> str:
        return self.addresse() + self.postal

    def serialize(self, backup=False):
        return {
            "pk": self.pk,
            "name": self.name,
            "porte": self.porte,
            "street": self.street,
            "city": self.city.name if backup else self.city.serialize(),
            "appart": self.appart,
            "joined": self.joined.strftime("%Y-%m-%d %H:%M:%S"),
            "postal": self.postal,
            "province": self.province,
            "email": self.email,
            "phone": self.phone,
            "statut": self.statut,
            "is_regulier": self.is_regulier,
            "is_prospect": self.is_prospect,
        }

    def claim(self):
        self.prospect = False
        self.save()

    def generate_from_tasks(self, obj: str, tasks: list[dict]):
        return Facture.generate(self, obj, tasks)

    @staticmethod
    def to_csv(filename="./backup/customers.csv"):
        fields = [
            "pk",
            "name",
            "porte",
            "street",
            "city",
            "appart",
            "joined",
            "postal",
            "province",
            "email",
            "phone",
            "statut",
            "is_regulier",
            "is_prospect",
        ]
        with open(filename, "w", encoding=ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            try:
                writer.writerows([c.serialize(True) for c in Customer.select()])
            except (Exception,) as e:
                print(e, e.args)
                return False
            else:
                return True

    @staticmethod
    def read_csv(filename="./backup/customers.csv"):
        fields = [
            "pk",
            "name",
            "porte",
            "street",
            "city",
            "appart",
            "joined",
            "postal",
            "province",
            "email",
            "phone",
            "statut",
            "is_regulier",
            "is_prospect",
        ]
        with open(filename, "r", encoding=ENCODING) as f:
            reader = csv.DictReader(f, fieldnames=fields, delimiter=";")
            Customer.delete().execute()
            with db.atomic():
                for customer in reader:
                    try:
                        c: Customer = Customer.create(**Customer.loads(customer))
                    except (Exception,) as e:
                        print(e)
                        pass
                    else:
                        print(f"Client {c.name} créé avec succès !")

    @staticmethod
    def loads(data: dict[str, str]):
        data["pk"] = int(data["pk"])
        data["porte"] = int(data["porte"])
        data["appart"] = int(data["appart"]) if data["appart"] else None
        data["city"], _ = City.get_or_create(name=data["city"])
        data["joined"] = dt.strptime(
            data["joined"],
            "%Y-%m-%d" if len(data["joined"]) == 10 else "%Y-%m-%d %H:%M:%S",
        )
        data["is_regulier"] = True if data["is_regulier"] == "True" else False
        data["is_prospect"] = True if data["is_prospect"] == "True" else False

        return data

    @staticmethod
    def clean(read: dict):
        r = {
            "name": read.get("name"),
            "porte": int(read.get("porte")),
            "street": read.get("street"),
            "city": read.get("city"),
            "appart": read.get("appart") if read.get("appart") else None,
            "joined": read.get("joined") if read.get("joined") else dt.today(),
            "postal": read.get("postal"),
            "province": read.get("province"),
            "email": read.get("email") if read.get("email") else None,
            "phone": read.get("phone") if read.get("phone") else None,
            "statut": read.get("statut"),
            "regulier": True if read.get("regulier") == "True" else False,
            "prospect": True if read.get("prospect") == "True" else False,
        }

        return r

    def __str__(self):
        return f"Client : {self.name}"

    def __repr__(self) -> str:
        return self.__str__()


class Organization(BaseModel):
    name = pw.CharField()
    slogan = pw.CharField()
    localization = pw.CharField()
    postal = pw.CharField(max_length=10)
    mail = pw.CharField()
    neq = pw.CharField(max_length=11)
    img = pw.CharField(default="media/img/entreprise.png")

    def __str__(self):
        return self.name

    def __repr__(self) -> str:
        return self.name


class Admin(BaseModel):
    name = pw.CharField()
    poste = pw.CharField()
    organization: Organization = pw.ForeignKeyField(Organization, backref="admins")
    phone = pw.CharField()
    mail = pw.CharField()
    img = pw.CharField(default="media/img/particulier.png")

    def __str__(self):
        return f"{self.name} from {self.organization}"

    def __repr__(self) -> str:
        return self.__str__()


class Facture(BaseModel):
    """Implémentation de la classe des factures"""

    hash = pw.CharField(primary_key=True)
    date: dt = pw.DateTimeField(default=dt.now)
    sent = pw.BooleanField(default=False)
    cout = pw.DecimalField()
    obj = pw.CharField()
    is_soumission = pw.BooleanField(default=False)
    customer: Customer = pw.ForeignKeyField(Customer, backref="factures")

    @staticmethod
    def clean(read: dict):
        return {
            "hash": read.get("hash"),
            "date": read.get("date"),
            "sent": True if read.get("sent") == "True" else False,
            "cout": float(read.get("cout")),
            "obj": read.get("obj"),
            "soumission": True if read.get("soumission") == "True" else False,
            "customer": int(read.get("customer")),
        }

    @staticmethod
    def to_csv(filename="./backup/factures.csv"):
        fields = ["hash", "date", "sent", "cout", "obj", "is_soumission", "customer"]
        with open(filename, "w", encoding=ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            try:
                writer.writerows([f.serialize(True) for f in Facture.select()])
            except (Exception,) as e:
                print(e, e.args)
                return False
            else:
                return True

    @staticmethod
    def read_csv(filename="./backup/factures.csv"):
        fields = ["hash", "date", "sent", "cout", "obj", "is_soumission", "customer"]
        with open(filename, "r", encoding=ENCODING) as f:
            reader = csv.DictReader(f, fieldnames=fields, delimiter=";")
            Facture.delete().execute()
            with db.atomic():
                for facture in reader:
                    try:
                        f: Facture = Facture.create(**Facture.loads(facture))
                    except (Exception,) as e:
                        print(e)
                        pass
                    else:
                        print(f"Facture {f.hash} créé avec succès !")

    @staticmethod
    def generate(customer: Customer, obj: str, tasks: list[dict]):
        """Unique implementation for all invoice generation"""
        maintenant = dt.now()
        _hash = hb.blake2b(
            f"RandomPack:{obj}:{int(time.time())}".encode(),
            digest_size=4,
            salt=os.getenv("HASH_SALT", "").encode(),
        ).hexdigest()
        _hash = f"{_hash}-{dt.today().year}-{customer.statut}"
        admin = Customer(
            name=os.getenv("ADMIN_FULLNAME"),
            adress=os.getenv("ADIMN_ADRESS"),
            phone=os.getenv("ADMIN_PHONE"),
            city=os.getenv("ADMIN_CITY"),
            email=os.getenv("EMAIL_USER"),
        )
        elements = [
            {
                "name": "logo",
                "type": "I",
                "size": 0.0,
                "align": "I",
                "x1": percent(5),
                "x2": percent(9),
                "y1": percent(4, True),
                "y2": percent(7, True),
            },
            {
                "name": "organizme",
                "type": "T",
                "size": 13,
                "bold": 1,
                "x1": percent(10),
                "x2": percent(55),
                "y1": percent(4, True),
                "y2": percent(4, True),
            },
            {
                "name": "facture-hash",
                "type": "T",
                "size": 17,
                "align": "R",
                "x1": percent(60),
                "x2": percent(95),
                "y1": percent(4.0, True),
                "y2": percent(4.0, True),
            },
            {
                "name": "organizme-billet",
                "type": "T",
                "size": 10,
                "x1": percent(10),
                "x2": percent(65),
                "y1": percent(4.1, True),
                "y2": percent(5.1, True),
                "multiline": True,
            },
            {
                "name": "admin-billet",
                "type": "T",
                "size": 11,
                "x1": percent(5),
                "x2": percent(50),
                "y1": percent(8.8, True),
                "y2": percent(10, True),
                "multiline": True,
            },
            {
                "name": "facture-object",
                "type": "T",
                "size": 11,
                "align": "R",
                "x1": percent(60),
                "x2": percent(95),
                "y1": percent(6, True),
                "y2": percent(7, True),
            },
            {
                "name": "facture-date",
                "type": "T",
                "size": 12,
                "align": "R",
                "x1": percent(60),
                "x2": percent(95),
                "y1": percent(7.0, True),
                "y2": percent(9.0, True),
            },
            {
                "name": "client-billet",
                "type": "T",
                "size": 11,
                "x1": percent(5),
                "x2": percent(50),
                "y1": percent(18.7, True),
                "y2": percent(20, True),
                "multiline": True,
            },
        ]

        # here we instantiate the template
        invoice = Template(
            format="A4",
            elements=elements,
            title=f'{"Soumission" if customer.is_prospect else "Facture"} {_hash}',
            author="Entretien Excellence",
            unit="mm",
            creator="FPDF 2",
            keywords="entretien excellence, facture",
            subject=f'{"Soumission" if customer.is_prospect else "Facture"} {_hash}',
        )

        invoice.add_page()

        # we FILL some of the fields of the template with the information we want
        # note we access the elements treating the template instance as a "dict"
        invoice["logo"] = "./static/assets/img/logos/android-chrome-192x192.png"
        invoice["organizme"] = "Entretien Excellence & Cie"
        invoice[
            "facture-hash"
        ] = f'{"Soumission" if customer.is_prospect else "Facture"} {_hash}'
        invoice[
            "organizme-billet"
        ] = """
Lavage de vitres - Recherche & Développement de solutions d'entretien durable\n
Mirabel, Québec
        """

        invoice[
            "admin-billet"
        ] = f"""
{admin.name}
Directeur des opérations commerciales
{admin.phone}
{admin.email}
NEQ : 2277408508
    """

        invoice["facture-object"] = f"Objet : {obj}"
        invoice["facture-date"] = maintenant.strftime("%Y-%m-%d")
        invoice[
            "client-billet"
        ] = f"""
{customer.name}
{customer.addresse()}
{customer.postal}
{customer.city.name}, {customer.province}
{customer.email if customer.email else ""}
    """
        total = sum((float(task.get("value", "0")) for task in tasks))
        data = (
            ("Désignation", "Montant"),
            *((task.get("name"), float(task.get("value", "0"))) for task in tasks),
            ("Sous total ", total),
            ("Taxes ", total * 0.1496),
            ("Total", total * 1.1496),
        )

        pdf: FPDF = invoice.pdf
        pdf.set_font("helvetica", size=12)
        if customer.is_prospect:
            pdf.set_y(percent(38, True))
            pdf.cell(
                txt=f"Cher {customer.name}, Entretien Excellence vous propose les services suivant : "
            )
        pdf.set_y(percent(40, True))
        line_height = pdf.font_size * 1.75
        col_width = pdf.epw / 2  # distribute content evenly
        for i, row in enumerate(data):
            if i in (0, len(data) - 1):
                pdf.set_font(style="B")
            else:
                pdf.set_font(style="")

            for j, col in enumerate(row):
                pdf.multi_cell(
                    col_width,
                    line_height,
                    f"{col:.2f} $" if i != 0 and j == 1 else col,
                    border=1,
                    align=("C" if j == 1 or i in (0, len(data) - 1) else "L"),
                    new_x="RIGHT",
                    new_y="TOP",
                    max_line_height=pdf.font_size,
                )
            pdf.ln(line_height)

        pdf.cell(txt=f"N° de taxes : {os.getenv('ADMIN_TVS')}\n")
        pdf.cell(txt="\n\n")
        # pdf.set_y(percent(60, True))
        pdf.set_font(style="", size=14)

        pdf.set_y(percent(75, True))
        pdf.cell(txt="Merci de votre confiance et à bientôt!")
        pdf.set_font(style="", size=12)
        pdf.set_x(percent(60))
        pdf.multi_cell(
            w=percent(45),
            h=percent(1.7, True),
            txt="""
Paiement par chèque au nom de:\nMarc-Antoine Cloutier\nVirement interac au markantoinecloutier@gmail.com\nou comptant
    """,
            align="L",
        )
        try:
            invoice.render(os.path.join(DOCS_PATH, f"{_hash}.pdf"))  # type: ignore
        except (Exception,) as e:
            print(e.__class__, e.args[0])
            statut, _ = False, e.args[0]
        else:
            statut, _ = True, _hash

        if statut:
            try:
                f = Facture.create(
                    hash=_hash,
                    customer=customer,
                    date=maintenant,
                    cout=total,
                    obj=obj,
                    is_soumission=customer.is_prospect,
                )
            except (pw.IntegrityError,):
                print("Same facture seems already exists.")
                f: Facture = Facture.get(hash=_hash)
            else:
                print(f"Facture {_hash} generated")
                if not f.is_soumission:
                    Event.create(
                        name=f.obj,
                        price=f.cout,
                        executed_at=maintenant,
                        customer=f.customer,
                        facture=f,
                    )
                f.regenerate()
            return True, f
        return False, _hash

    @staticmethod
    def loads(data: dict):
        return {
            "hash": data["hash"],
            "date": dt.strptime(
                data["date"],
                "%Y-%m-%d" if len(data["date"]) == 10 else "%Y-%m-%d %H:%M:%S",
            ),
            "sent": True if data["sent"] == "True" else False,
            "cout": float(data["cout"]),
            "obj": data["obj"],
            "is_soumission": True if data["is_soumission"] == "True" else False,
            "customer": Customer.get(pk=int(data["customer"])),
        }

    def serialize(self, backup=False):
        return {
            "hash": self.hash,
            "date": self.date.strftime("%Y-%m-%d %H:%M:%S"),
            "sent": self.sent,
            "cout": self.cout,
            "obj": self.obj,
            "is_soumission": self.is_soumission,
            "customer": self.customer.pk if backup else self.customer.serialize(),
        }

    def regenerate(self):
        src = os.path.join(DOCS_PATH, f"{self.hash}.pdf")
        dest = os.path.join(
            COMPTA_PATH, f"{self.customer.statut}", f"{self.customer.name}"
        )
        os.makedirs(dest, exist_ok=True)
        try:
            shutil.copy(src, dest)
        except (FileNotFoundError,):
            return False
        else:
            return True

    def send(self, corps, mailer):
        if not self.sent and self.customer.email:
            try:
                r = mailer.send_message(
                    self.customer.email,
                    self.obj,
                    corps,
                    [os.path.join(os.getenv("DOCS_PATH"), f"{self.hash}.pdf")],
                )
            except (Exception,) as e:
                print(
                    f"{e.__class__} {e.args[0]} in sending mail to {self.customer.email}"
                )
            else:
                self.sent = True
                self.save()
                if not self.is_soumission:
                    self.regenerate()
                print(f"Facture {self.hash} send to {self.customer}.")

                return True
        else:
            return False

    def delete_(self):
        try:
            os.remove(os.path.join(DOCS_PATH, f"{self.hash}.pdf"))
            os.remove(
                os.path.join(
                    COMPTA_PATH,
                    f"{self.customer.statut}",
                    f"{self.customer.name}",
                    f"{self.hash}.pdf",
                )
            )
        except (FileNotFoundError,):
            pass
        except (Exception,) as e:
            print(f"{e.__class__} : {e.args[0]}")
        finally:
            self.delete_instance()
            print(f"Facture {self.hash} successfully deleted")

    def ht(self):
        return sum((task.price for task in self.tasks))

    def ttc(self):
        return round(self.ht() * 1.14975, 2)

    def __str__(self):
        return f"Facture de {self.customer} pour {self.obj}"

    def __repr__(self) -> str:
        return self.__str__()


class Event(BaseModel):
    pk = pw.IntegerField(primary_key=True)
    name = pw.CharField()
    price = pw.FloatField(null=True, default=None)
    executed_at: dt = pw.DateTimeField(default=dt.now)
    customer: Customer = pw.ForeignKeyField(Customer, backref="tasks")
    facture: Facture = pw.ForeignKeyField(
        Facture, backref="tasks", null=True, default=None
    )

    @staticmethod
    def clean(read: dict):
        return {
            "pk": int(read.get("pk")),
            "name": read.get("name"),
            "price": float(read.get("price")),
            "executed_at": read.get("executed_at"),
            "customer": int(read.get("customer")),
            "facture": read.get("facture"),
        }

    def serialize(self):
        return {
            "pk": self.pk,
            "name": self.name,
            "price": self.price,
            "executed_at": self.executed_at.strftime("%Y-%m-%d %H:%M:%S"),
            "customer": self.customer.serialize(),
            "facture": self.facture.serialize(),
        }

    def defacturer(self):
        self.facture = None
        self.save()

    @staticmethod
    def parse_agenda_event(event: dict):
        name = event["summary"]
        customer: Customer = Customer.get(Customer.name.ilike(name))
        subtasks = list()
        clauses = event.get("description").split("\n")
        for s, p in [clause.strip().split("-") for clause in clauses]:
            subtasks.append(
                {"service": s.strip().lower().capitalize(), "value": float(p.strip())}
            )

        return {
            "customer": customer.serialize(),
            "subtasks": subtasks,
            "start": event["start"]["dateTime"].removesuffix("Z").replace("T", " "),
            "url": event["htmlLink"],
            "montant": sum([s.get("value", 0) for s in subtasks]),
        }

    def __str__(self):
        return f"{self.name} for {self.customer}"

    def __repr__(self) -> str:
        return self.__str__()


class SubTask(BaseModel):
    pk = pw.IntegerField(primary_key=True)
    name = pw.CharField()

    @staticmethod
    def to_csv(filename="./backup/subtasks.csv"):
        fields = ["pk", "name"]
        with open(filename, "w", encoding=ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            writer.writerows([s.serialize() for s in SubTask.select()])

        return True

    @staticmethod
    def read_csv(filename="./backup/subtasks.csv"):
        fields = ["pk", "name"]
        with open(filename, "r", encoding=ENCODING) as f:
            SubTask.delete().execute()
            reader = csv.DictReader(f, fieldnames=fields, delimiter=";")
            with db.atomic():
                for subtask in reader:
                    s = SubTask.create(**SubTask.loads(subtask))
                    print(f"Service {s.name} créé avec succès !")
        return True

    @staticmethod
    def loads(data):
        return {
            "pk": int(data["pk"]),
            "name": data["name"],
        }

    @staticmethod
    def clean(read: dict):
        return {
            "pk": int(read.get("pk")),
            "name": read.get("name"),
        }

    def serialize(self):
        return {"pk": self.pk, "name": self.name}

    def __str__(self):
        return self.name


class Pack(BaseModel):
    pk = pw.IntegerField(primary_key=True)
    name = pw.CharField()
    customer: Customer = pw.ForeignKeyField(Customer, unique=True, backref="pack")

    @staticmethod
    def to_csv(filename="./backup/packs.csv"):
        fields = ["pk", "name", "customer"]
        with open(filename, "w", encoding=ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            writer.writerows([p.dumps() for p in Pack.select()])

        return True

    @staticmethod
    def read_csv(filename="./backup/packs.csv"):
        fields = ["pk", "name", "customer"]
        with open(filename, "r", encoding=ENCODING) as f:
            reader = csv.DictReader(f, fieldnames=fields, delimiter=";")
            Pack.delete().execute()
            with db.atomic():
                for pack in reader:
                    try:
                        p: Pack = Pack.create(**Pack.loads(pack))
                    except (Exception,) as e:
                        print(e, e.args)
                    else:
                        print(f"Pack {p.name} créé avec succès !")

    @staticmethod
    def loads(data: dict):
        return {
            "pk": int(data["pk"]),
            "name": data["name"],
            "customer": int(data["customer"]),
        }

    def dumps(self):
        return {"pk": self.pk, "name": self.name, "customer": self.customer.pk}

    @staticmethod
    def clean(read: dict):
        return {
            "pk": int(read.get("pk")),
            "name": read.get("name"),
            "customer": int(read.get("customer")),
        }

    def generate_facture(self, obj) -> tuple[bool, Facture]:
        tasks: list[PackSubTask] = (
            PackSubTask.select().join(Pack).where(Pack.customer == self.customer)
        )
        tasks = [task.serialize() for task in tasks]
        tasks = [
            {"name": task["subtask"]["name"], "value": task["value"]} for task in tasks
        ]

        return Facture.generate(self.customer, obj, tasks)

    def price(self):
        return float(
            sum(
                [
                    psub.value if psub.value else 0
                    for psub in PackSubTask.select()
                    .join(Pack)
                    .where(Pack.customer == self.customer)
                ]
            )
        )

    def serialize(self):
        return {
            "pk": self.pk,
            "name": self.name,
            "price": self.price(),
            "customer": self.customer.serialize(),
            "subtasks": [
                st.serialize()
                for st in PackSubTask.select().where(PackSubTask.pack == self)
            ],
        }

    def __str__(self):
        return f"{self.name} de {self.customer.name}"


class PackSubTask(BaseModel):
    value = pw.DecimalField(default=0.00, null=True)
    subtask: SubTask = pw.ForeignKeyField(SubTask)
    pack: Pack = pw.ForeignKeyField(Pack, on_delete="CASCADE", backref="subtasks")

    @staticmethod
    def to_csv(filename="./backup/packsubtasks.csv"):
        fields = ["value", "subtask", "pack"]
        with open(filename, "w", encoding=ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            writer.writerows([p.dumps() for p in PackSubTask.select()])

        return True

    @staticmethod
    def read_csv(filename="./backup/packsubtasks.csv"):
        fields = ["value", "subtask", "pack"]
        with open(filename, "r", encoding=ENCODING) as f:
            reader = csv.DictReader(f, fieldnames=fields, delimiter=";")
            PackSubTask.delete().execute()
            with db.atomic():
                for pack in reader:
                    try:
                        p: PackSubTask = PackSubTask.create(**PackSubTask.loads(pack))
                    except (Exception,) as e:
                        print(e, e.args)
                    else:
                        print(
                            f"Service {p.subtask.name} ajouté au pack {p.pack.name} avec succès !"
                        )

    @staticmethod
    def loads(data):
        return {
            "value": float(data["value"]),
            "subtask": int(data["subtask"]),
            "pack": int(data["pack"]),
        }

    def dumps(self):
        return {"value": self.value, "subtask": self.subtask.pk, "pack": self.pack.pk}

    def serialize(self):
        return {
            "pk": self.id,
            "subtask": self.subtask.serialize(),
            "value": float(self.value if self.value else 0),
        }

    def __str__(self) -> str:
        return f"{self.subtask.name} : {self.value} $ in pack {self.pack}"


class ListProduction(BaseModel):
    pk = pw.IntegerField(primary_key=True)
    name = pw.CharField(unique=True)

    def serialize(self):
        return {
            "pk": self.pk,
            "name": self.name,
            "price": round(self.price(), 2),
            "packs": [
                lp.pack.serialize()
                for lp in ListPack.select().where(ListPack.prod == self)
            ],
        }

    @staticmethod
    def to_csv(filename="./backup/listproductions.csv"):
        fields = ["pk", "name"]
        with open(filename, "w", encoding=ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            writer.writerows([lp.dumps() for lp in ListProduction.select()])

        return True

    @staticmethod
    def read_csv(filename="./backup/listproductions.csv"):
        fields = ["pk", "name"]
        with open(filename, "r", encoding=ENCODING) as f:
            reader = csv.DictReader(f, fieldnames=fields, delimiter=";")
            ListProduction.delete().execute()
            with db.atomic():
                for prod in reader:
                    try:
                        lp: ListProduction = ListProduction.create(
                            **ListProduction.loads(prod)
                        )
                    except (Exception,) as e:
                        print(e, e.args)
                    else:
                        print(f"Liste de production {lp.name} créé avec succès !")

        return True

    def dumps(self):
        return {"pk": self.pk, "name": self.name}

    @staticmethod
    def loads(data):
        return {"pk": int(data["pk"]), "name": data["name"]}

    def price(self):
        return sum(
            [lp.pack.price() for lp in ListPack.select().where(ListPack.prod == self)]
        )

    def __str__(self):
        return self.name


class ListPack(BaseModel):
    pack: Pack = pw.ForeignKeyField(Pack)
    prod: ListProduction = pw.ForeignKeyField(ListProduction)

    @staticmethod
    def to_csv(filename="./backup/listpacks.csv"):
        fields = ["pack", "prod"]
        with open(filename, "w", encoding=ENCODING) as f:
            writer = csv.DictWriter(f, fieldnames=fields, delimiter=";")
            writer.writerows([lp.dumps() for lp in ListPack.select()])
        return True

    @staticmethod
    def read_csv(filename="./backup/listpacks.csv"):
        fields = ["pack", "prod"]
        with open(filename, "r", encoding=ENCODING) as f:
            reader = csv.DictReader(f, fieldnames=fields, delimiter=";")
            ListPack.delete().execute()
            with db.atomic():
                for listpack in reader:
                    try:
                        lp: ListPack = ListPack.create(**ListPack.loads(listpack))
                    except (Exception,) as e:
                        print(e, e.args)
                    else:
                        print(
                            f"Pack {lp.pack.name} ajouté à la liste de production {lp.prod.name}"
                        )

    @staticmethod
    def loads(data):
        return {"pack": int(data["pack"]), "prod": int(data["prod"])}

    def dumps(self) -> dict:
        return {"pack": self.pack.pk, "prod": self.prod.pk}

    def serialize(self):
        return {
            "pk": self.id,
            "pack": self.pack.serialize(),
            "prod": self.prod.serialize(),
        }


if __name__ == "__main__":
    args = parser.parse_args()
    if args.cmd == "create-tables":
        print("Creating tables ...")
        db.create_tables(
            [
                City,
                Customer,
                Pack,
                Facture,
                SubTask,
                PackSubTask,
                Organization,
                Admin,
                Event,
                ListPack,
                ListProduction,
            ]
        )
        print("Tables created !")
    elif args.cmd == "create-dirs":
        for path in (DOCS_PATH, BACKUP_PATH, COMPTA_PATH, FILES_PATH):
            # os.makedirs(path, exist_ok=True)
            print(f"{path} créé !")
