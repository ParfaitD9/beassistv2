import os
import sys
import json
from datetime import datetime as dt

import peewee as pw
from flask import Flask, render_template, request, send_from_directory
from flask.json import jsonify

from ut1ls.mailer import Agenda, Mailer
from ut1ls.orm import (
    City,
    Customer,
    Event,
    Facture,
    ListPack,
    ListProduction,
    Pack,
    PackSubTask,
    SubTask,
    db,
)

app = Flask(__name__)
# server = Process(target=app.run, kwargs={'port':8000, 'debug':True})


m = Mailer()
ag = Agenda()
ENCODING = sys.getfilesystemencoding()


@app.route("/")
def dashboard():
    return render_template("rwtd/dashboard.html", **{"actual": "Tableau de bord"})


@app.route("/customers")
def customers():
    return render_template("rwtd/customers.html", **{"actual": "Clients"})


@app.route("/packs")
def packs():
    return render_template("rwtd/packs.html", **{"actual": "Contrats"})


@app.route("/pack/<int:pk>")
def pack(pk):
    try:
        pack: Pack = Pack.get(pk=pk)
    except (pw.DoesNotExist,) as e:
        pass
    else:
        return render_template("rwtd/pack.html", **{"actual": "Contrats", "pack": pack})


@app.route("/factures")
def factures():
    return render_template("rwtd/factures.html", **{"actual": "Factures"})


@app.route("/productions")
def productions():
    return render_template("rwtd/productions.html", **{"actual": "Productions"})


@app.route(
    "/shutdown",
    methods=[
        "POST",
    ],
)
def shutdown():
    print(request.environ)
    return jsonify(
        {"success": True, "message": "Server has been shutdown !", "data": {}}
    )


# API endpoints

# Customer endpoints
@app.route(
    "/api/v1/customer/create",
    methods=[
        "POST",
    ],
)
def api_customer_create():
    data = request.form.to_dict()
    try:
        city, _ = City.get_or_create(name=data.get("city"))
        data.update({"city": city.pk})
        data.update(
            {"is_regulier": True if request.form.get("is_regulier") == "on" else False}
        )
        data.update(
            {"is_prospect": True if request.form.get("is_prospect") == "on" else False}
        )
        c = Customer.create(**data)
    except (Exception,) as e:
        r = {"success": False, "data": "", "message": f"{e.__class__} : {e.args[0]}"}
    else:
        r = {
            "success": True,
            "data": c.serialize(),
            "message": f"Utilisateur {c.name} créé avec succès",
        }

    return jsonify(r)


@app.route("/api/v1/customers")
def api_customers():
    irr = request.args.get("irreguliers", type=int)
    prosp = request.args.get("prospects", type=int)
    name = request.args.get("name", "").strip()
    query: pw.ModelSelect = Customer.select()
    if name:
        query = query.where(Customer.name.contains(name))
    if prosp:
        query = query.where(Customer.is_prospect == bool(prosp))
    if irr:
        query = query.where(Customer.is_regulier == bool(irr))

    cs = [c.serialize() for c in query.order_by(Customer.name.asc())]
    return jsonify({"success": True, "data": cs, "message": ""})


@app.route("/api/v1/customer/<int:pk>")
def api_customer(pk):
    try:
        c: Customer = Customer.get(pk=pk)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        r = {"success": True, "data": c.serialize(), "message": "Utilisateur trouvé"}

    return jsonify(r)


@app.route(
    "/api/v1/customer/update/<int:pk>",
    methods=[
        "POST",
    ],
)
def api_customer_update(pk):
    u: Customer = Customer.get(pk=pk)

    data = request.form.to_dict()
    data.update({"city": City.get(name=request.form.get("city"))})
    data.update(
        {"is_regulier": True if request.form.get("is_regulier") == "on" else False}
    )
    data.update(
        {"is_prospect": True if request.form.get("is_prospect") == "on" else False}
    )
    try:
        query = Customer.update(**data).where(Customer.pk == pk)
        query.execute()
    except (Exception,) as e:
        r = {
            "success": False,
            "data": "",
            "message": e.args[0],
        }
    else:
        u: Customer = Customer.get(pk=pk)
        r = {
            "success": True,
            "data": u.serialize(),
            "message": f"Client {u.name} modifié",
        }

    return jsonify(r)


@app.route(
    "/api/v1/customer/facture/<int:pk>",
    methods=[
        "POST",
    ],
)
def api_customer_facture(pk):
    try:
        c: Customer = Customer.get(pk=pk)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        p: list[Pack] = Pack.select().join(Customer).where(Customer.pk == c.pk)
        if p:
            month = dt.today().strftime("%B %Y")
            success, f = p[0].generate_facture(
                f"Soumision - Entretien Excellence"
                if p[0].customer.is_prospect
                else f"Entretien Excellence - Lavage de vitres - {month}"
            )

            r = {
                "success": success,
                "data": f.serialize() if success else f,
                "message": f"Facture {f.hash} générée !"
                if success
                else f"Erreur lors de la génération {f}",
            }

        else:
            r = {
                "success": True,
                "data": c.serialize(),
                "message": f"Pas de pack trouvé pour {c.name}",
            }

    return jsonify(r)


@app.route(
    "/api/v1/customer/delete/<int:pk>",
    methods=[
        "POST",
    ],
)
def api_customer_delete(pk):
    try:
        c: Customer = Customer.get(pk=pk)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        c.delete_instance(recursive=True)
        r = {"success": True, "data": pk, "message": "Utilisateur supprimé"}

    return jsonify(r)


# Packs endpoints
@app.route(
    "/api/v1/pack/create",
    methods=[
        "POST",
    ],
)
def api_pack_create():
    pack: dict = json.loads(request.form.get("data"))

    c: Customer = Customer.get(pk=int(pack["customer"]))

    with db.atomic():
        try:
            p = Pack.create(name=pack.get("name"), customer=c)
        except (pw.IntegrityError,) as e:
            return jsonify(
                {
                    "success": False,
                    "data": "",
                    "message": f"{e.__class__} : {e.args[0]}",
                }
            )
        else:
            for sub in pack.get("subtasks"):
                s, _ = SubTask.get_or_create(name=sub.get("name"))
                ps = PackSubTask.create(subtask=s, pack=p, value=sub.get("value"))

            return jsonify(
                {
                    "success": True,
                    "data": p.serialize(),
                    "message": "Pack créé avec succès",
                }
            )


@app.route("/api/v1/packs")
def api_packs():
    soumissions = request.args.get("soumissions", type=int)
    search = request.args.get("search", "").strip()

    query: pw.ModelSelect = Pack.select().join(Customer)
    if soumissions:
        query: pw.ModelSelect = query.where(Customer.is_prospect == bool(soumissions))
    if search:
        if search[0] == "!":
            query = query.where(Customer.name.contains(search[1:]))
        else:
            query = query.where(Pack.name.contains(search))
    ps = [p.serialize() for p in query.order_by(Pack.pk.desc())]
    return jsonify({"success": True, "data": ps, "message": ""})


@app.route("/api/v1/pack/<int:pk>")
def api_pack(pk):
    try:
        p: Pack = Pack.get(pk=pk)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        r = {"success": True, "data": p.serialize(), "message": "Pack trouvé"}

    return jsonify(r)


@app.route("/api/v1/pack/update/<int:pk>", methods=["POST"])
def api_pack_update(pk):
    try:
        pack: Pack = Pack.get(pk=pk)
    except (Exception,) as e:
        return jsonify({"success": False, "data": "", "message": f"{e.args}"})
    else:
        pack.name = request.form.get("packName")
        pack.save()

        return jsonify(
            {
                "success": True,
                "data": pack.serialize(),
                "message": f"Changements effectifs sur {pack.name}",
            }
        )


@app.route(
    "/api/v1/pack/delete/<int:pk>",
    methods=[
        "POST",
    ],
)
def api_pack_delete(pk):
    try:
        p: Pack = Pack.get(pk=pk)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        p.delete_instance(recursive=True)
        r = {"success": True, "data": p.serialize(), "message": "Pack supprimé"}

    return jsonify(r)


@app.route(
    "/api/v1/pack/facture/<int:pk>",
    methods=[
        "POST",
    ],
)
def api_pack_facture(pk):
    obj = request.form.get("obj")
    try:
        p: Pack = Pack.get(pk=pk)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        s, f = p.generate_facture(obj)
        r = {
            "success": s,
            "data": f.serialize() if s else f,
            "message": f"Pack facturé à {f.hash}" if s else f,
        }

    return jsonify(r)


# Subtask endpoints
@app.route(
    "/api/v1/subtask/create",
    methods=[
        "POST",
    ],
)
def api_subtask_create():
    try:
        data = request.form.to_dict()
        st: SubTask = SubTask.create(**data)
    except (Exception,) as e:
        r = {"success": False, "data": "", "message": f"{e.__class__} : {e.args[0]}"}
    else:
        r = {
            "success": True,
            "data": st.serialize(),
            "message": "Nouveau service créé avec succès",
        }
    return jsonify(r)


@app.route("/api/v1/subtasks")
def api_subtasks():
    sts = [st.serialize() for st in SubTask.select().order_by(SubTask.name.asc())]
    return jsonify({"success": True, "data": sts, "message": ""})


@app.route("/api/v1/subtask/<int:pk>")
def api_subtask(pk):
    try:
        st: SubTask = SubTask.get(pk=pk)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        r = {"success": True, "data": st.serialize(), "message": ""}

    return jsonify(r)


@app.route(
    "/api/v1/subtask/delete/<int:pk>",
    methods=[
        "POST",
    ],
)
def api_subtask_delete(pk):
    try:
        st: SubTask = SubTask.get(pk=pk)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        st.delete_instance(recursive=True)
        r = {"success": True, "data": st.serialize(), "message": "Service retiré"}

    return jsonify(r)


# Facture endpoints
@app.route("/api/v1/facture/create", methods=["POST"])
def api_facture_create():
    facture: dict = json.loads(request.form.get("data"))
    c: Customer = Customer.get(pk=int(facture.get("customer")))
    statut, f = c.generate_from_tasks(facture.get("obj"), facture.get("subtasks"))

    return jsonify(
        {
            "success": statut,
            "data": f.serialize() if statut else f,
            "message": f"Facture {f.hash} générée"
            if statut
            else f"Erreur lors de la génération de la facture {f}",
        }
    )


@app.route("/api/v1/factures")
def api_factures():
    soumissions = request.args.get("soumissions", type=int)
    notsent = request.args.get("notsent", type=int)
    _hash = request.args.get("hash", "").strip()

    query: pw.ModelSelect = Facture.select().join(Customer)
    if _hash:
        if _hash[0] == "!":
            query = query.where(Customer.name.contains(_hash[1:]))
        else:
            query = query.where(Facture.hash.contains(_hash))

    if soumissions:
        query = query.where(Customer.is_prospect == bool(soumissions))
    if notsent:
        query = query.where(Facture.sent != bool(notsent))
    fs = [f.serialize() for f in query.order_by(Facture.date.desc())]
    return jsonify({"success": True, "data": fs, "message": ""})


@app.route("/api/v1/facture/<hash>")
def api_facture(hash):
    try:
        f: Facture = Facture.get(hash=hash)
    except (Exception,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        r = {"success": True, "data": f.serialize(), "message": f"Facture {f.hash}"}

    return jsonify(r)


@app.route(
    "/api/v1/facture/delete/<hash>",
    methods=[
        "POST",
    ],
)
def api_facture_delete(hash):
    try:
        f: Facture = Facture.get(hash=hash)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        f.delete_()
        r = {"success": True, "data": f.serialize(), "message": "Facture supprimé"}

    return jsonify(r)


@app.route(
    "/api/v1/facture/send/<hash>",
    methods=[
        "POST",
    ],
)
def api_facture_send(hash):
    body = request.form.get("msg", "Message sur la facture à envoyer.")
    try:
        f: Facture = Facture.get(hash=hash)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        f.send(body.strip(), m)
        r = {
            "success": True,
            "data": f.serialize(),
            "message": f"Facture {f.hash} bien envoyée à {f.customer.name}",
        }

    return jsonify(r)


@app.route(
    "/api/v1/facture/class/<hash>",
    methods=[
        "POST",
    ],
)
def api_facture_class(hash):
    try:
        f: Facture = Facture.get(hash=hash)
    except (pw.DoesNotExist,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        if f.regenerate():
            r = {
                "success": True,
                "data": f.serialize(),
                "message": f"Facture {hash} classée avec succès !",
            }
        else:
            r = {
                "success": True,
                "data": f.serialize(),
                "message": f"Fichier de facture {hash} non existant",
            }
    return jsonify(r)


@app.route("/api/v1/facture/view/<hash>")
def api_facture_view(hash):
    if os.path.exists(os.path.join(os.getenv("DOCS_PATH"), f"{hash}.pdf")):
        return send_from_directory(os.getenv("DOCS_PATH"), f"{hash}.pdf")
    else:
        return "Facture non disponible sur cette machine."


# Production endpoints
@app.route("/api/v1/production/create", methods=["POST"])
def api_production_create():
    name = request.form.get("list-name")
    packs = request.form.getlist("packs")
    try:
        with db.atomic():
            lp = ListProduction.create(name=name)
            for _id in packs:
                pack = Pack.get(pk=int(_id))
                ListPack.create(pack=pack, prod=lp)
    except (Exception,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        lp: ListProduction = ListProduction.get(name=name)
        r = {
            "success": True,
            "data": lp.serialize(),
            "message": "Liste de production bien crée",
        }
    return jsonify(r)


@app.route("/api/v1/productions")
def api_productions():
    ls = [lp.serialize() for lp in ListProduction.select()]
    return jsonify({"success": True, "data": ls, "message": ""})


@app.route("/api/v1/production/<int:pk>")
def api_production(pk):
    try:
        prod: ListProduction = ListProduction.get(pk=pk)
    except (Exception,) as e:
        return jsonify({"success": False, "data": "", "message": e.args[0]})
    else:
        return jsonify({"success": True, "data": prod.serialize(), "message": ""})


@app.route("/api/v1/production/update/<int:pk>", methods=["POST"])
def api_production_update(pk):
    try:
        prod: ListProduction = ListProduction.get(pk=pk)
    except (pw.DoesNotExist) as e:
        return jsonify(
            {"success": False, "data": "", "message": f"{e.__class__} : {e.args}"}
        )
    else:
        new = request.form.get("prodName", "")
        if new.strip():
            prod.name = new.strip().capitalize()
            prod.save()

        return jsonify(
            {
                "success": True,
                "data": prod.serialize(),
                "message": f"Changement de nom pour {prod.name}",
            }
        )


@app.route("/api/v1/production/delete/<int:pk>", methods=["POST"])
def api_production_delete(pk):
    try:
        prod: ListProduction = ListProduction.get(pk=pk)
    except (Exception,) as e:
        return jsonify({"success": False, "data": "", "message": e.args[0]})
    else:
        prod.delete_instance(recursive=True)
        return jsonify({"success": True, "data": prod.serialize(), "message": ""})


@app.route(
    "/api/v1/production/send/<int:pk>",
    methods=[
        "POST",
    ],
)
def api_production_send(pk):
    msg = request.form.get("msg", "Petit message à ajouter")
    obj = request.form.get("obj", "Facture depuis entretien excellence")
    try:
        prod: ListProduction = ListProduction.get(pk=pk)
    except (Exception,) as e:
        r = {"success": False, "data": "", "message": e.args[0]}
    else:
        packs: list[Pack] = [
            lp.pack for lp in ListPack.select().where(ListPack.prod == prod)
        ]
        started = dt.now().strftime("%Y-%m-%dT%H:%M:%S")
        for pack in packs:
            try:
                statut, facture = pack.generate_facture(obj)
                facture: Facture
                if statut:
                    facture.send(msg, m)
                else:
                    with open(
                        f"./logs/production-{started}.log", "w", encoding=ENCODING
                    ) as writer:
                        txt = "[%(type)s] %(time)s %(errors)s\n"
                        writer.write(
                            txt
                            % {
                                "type": "ERROR",
                                "time": dt.now().strftime("%Y-%m-%dT%H:%M:%S"),
                                "errors": f"Impossible de générer une facture pour le pack de {pack.customer}",
                            }
                        )
            except (Exception,) as e:
                return jsonify(
                    {
                        "success": False,
                        "data": pack.serialize(),
                        "message": f"Erreur {e.args[0]} au pack {pack.name}",
                    }
                )
        else:
            r = {
                "success": True,
                "data": prod.serialize(),
                "message": f"Liste de production {prod.name} facturé avec succès",
            }
    return jsonify(r)


# List pack endpoints
@app.route("/api/v1/listpack/create", methods=["POST"])
def api_listpack_create():
    prod: ListProduction = ListProduction.get(pk=request.form.get("pk", type=int))
    pack: Pack = Pack.get(pk=request.form.get("to-add", type=int))

    lp = ListPack.create(prod=prod, pack=pack)

    return jsonify(
        {
            "success": True,
            "data": lp.serialize(),
            "message": f"Contrat {pack.name} ajouté à la liste {prod.name}",
        }
    )


@app.route("/api/v1/listpacks")
def api_listpacks():
    query = ListPack.select().join(ListProduction)
    pack = request.args.get("pack", 0, type=int)
    prod = request.args.get("prod", 0, type=int)

    if pack:
        query = query.where(Pack.pk == pack)

    if prod:
        query = query.where(ListProduction.pk == prod)

    return jsonify(
        {"success": True, "data": [q.serialize() for q in query], "message": ""}
    )


@app.route("/api/v1/listpack/delete/<int:pk>", methods=["POST"])
def api_listpack_delete(pk):
    try:
        lp: ListPack = ListPack.get_by_id(pk)
    except (pw.DoesNotExist,):
        return jsonify({"success": False, "data": "", "message": f"Lien non trouvé"})
    else:
        lp.delete_instance()
        return jsonify(
            {
                "success": True,
                "data": lp.serialize(),
                "message": f"{lp.pack.name} retiré de {lp.prod.name}",
            }
        )


# API Packsubtask
@app.route(
    "/api/v1/packsubtask/create",
    methods=[
        "POST",
    ],
)
def api_packsubtask_create():
    pack = request.form.get("pk", type=int)
    subtask = request.form.get("subtask")
    value = request.form.get("value", type=float)
    pack = Pack.get(pk=pack)
    subtask, _ = SubTask.get_or_create(name=subtask)

    try:
        p = PackSubTask.create(pack=pack, subtask=subtask, value=value)
    except (Exception,) as e:
        return jsonify({"success": False, "data": "", "message": f"{e.args}"})
    else:
        return jsonify(
            {
                "success": True,
                "data": p.serialize(),
                "message": f"{p.subtask.name} ajouté au contrat {p.pack.name}",
            }
        )


@app.route("/api/v1/packsubtasks")
def api_packsubtasks():
    pack = request.args.get("pack", 0, type=int)

    query: pw.ModelSelect = PackSubTask.select().join(Pack)
    if pack:
        query: list[PackSubTask] = query.where(Pack.pk == pack)

    return jsonify(
        {
            "success": True,
            "data": [q.serialize() for q in query],
            "message": f"{query.count()} services trouvés",
        }
    )


@app.route(
    "/api/v1/packsubtask/<int:pk>",
    methods=[
        "POST",
    ],
)
def api_packsubtask(pk):
    try:
        p = PackSubTask.get(id=pk)
    except (pw.DoesNotExist,) as e:
        pass
    else:
        return jsonify({"success": True, "data": p.serialize(), "message": ""})


@app.route(
    "/api/v1/packsubtask/delete/<int:pk>",
    methods=[
        "POST",
    ],
)
def api_packsubtask_delete(pk):
    try:
        p: PackSubTask = PackSubTask.get(id=pk)
    except (pw.DoesNotExist,) as e:
        pass
    else:
        p.delete_instance()
        return jsonify(
            {
                "success": True,
                "data": p.serialize(),
                "message": f"{p.subtask.name} retiré du contrat {p.pack.name}",
            }
        )


# Utilitaires endpoints
@app.route(
    "/api/v2/backup/<action>",
    methods=[
        "POST",
    ],
)
def api_backup(action):
    if action == "backup":
        City.to_csv()
        Customer.to_csv()
        Pack.to_csv()
        SubTask.to_csv()
        PackSubTask.to_csv()
        ListProduction.to_csv()
        ListPack.to_csv()

        msg = "Toutes les informations actuelles ont été sauvegardés"
    elif action == "load-backup":
        City.read_csv()
        Customer.read_csv()
        Pack.read_csv()
        SubTask.read_csv()
        PackSubTask.read_csv()
        ListProduction.read_csv()
        ListPack.read_csv()

        msg = "Les informations ont été bien chargées en base de données"
    else:
        msg = "Votre requête n'a pas pu être prise en compte."
    return jsonify(
        {
            "success": True,
            "message": msg,
            "data": "",
        }
    )


@app.route("/api/v2/state")
def api_state():
    moneyCeMois = (
        Facture.select(pw.fn.SUM(Facture.cout))
        .where(Facture.date.month == dt.today().month)
        .scalar()
    )
    moneyCeMois = moneyCeMois if moneyCeMois else 0

    moneySumTotal = Facture.select(pw.fn.SUM(Facture.cout)).scalar()
    moneySumTotal = moneySumTotal if moneySumTotal else 0

    moneySentCeMois = (
        Facture.select(pw.fn.SUM(Facture.cout))
        .where(Facture.sent & Facture.date.month == dt.today().month)
        .scalar()
    )
    moneySentCeMois = moneySentCeMois if moneySentCeMois else 0

    moneySentTotal = (
        Facture.select(pw.fn.SUM(Facture.cout)).where(Facture.sent).scalar()
    )
    moneySentTotal = moneySentTotal if moneySentTotal else 0

    factureCeMois = (
        Facture.select().where(Facture.date.month == dt.today().month).count()
    )
    factureTotal = Facture.select().count()
    factureCeMoisSent = (
        Facture.select()
        .where(Facture.sent & Facture.date.month == dt.today().month)
        .count()
    )
    factureSentTotal = Facture.select().where(Facture.sent).count()

    clientTotal = Customer.select().count()
    clientCeMois = (
        Customer.select().where(Customer.joined.month == dt.today().month).count()
    )

    packTotal = Pack.select().count()
    serviceTotal = SubTask.select().count()

    return jsonify(
        {
            "success": True,
            "data": {
                "fixed": {
                    "moneyMonth.value": moneyCeMois,
                    "moneyMonth.percent": round((moneyCeMois / moneySumTotal) * 100, 2),
                    "moneyMonth.sent": moneySentCeMois,
                    "factureMonth.value": factureCeMois,
                    "factureMonth.percent": round(
                        (factureCeMois / factureTotal) * 100, 2
                    ),
                    "factureMonth.sent": factureCeMoisSent,
                    "clientMonth.value": clientCeMois,
                    "clientMonth.percent": round((clientCeMois / clientTotal) * 100, 2),
                    "moneySentTotal": round(moneySentTotal, 2),
                    "moneyTotal.value": round(moneySumTotal, 2),
                    "clientTotal": clientTotal,
                    "factureSentTotal": factureSentTotal,
                    "packTotal": packTotal,
                    "serviceTotal": serviceTotal,
                    "factureTotal": factureTotal,
                }
            },
            "message": "",
        }
    )


@app.route("/api/v2/agenda")
def api_agenda():
    limit = request.args.get("limit", 16, type=int)
    try:
        events = ag.events(limit=limit)
    except (Exception,) as e:
        return jsonify(
            {"success": False, "data": "", "message": f"{e.__class__}: {e.args}"}
        )
    else:
        return jsonify(
            {
                "success": True,
                "data": [Event.parse_agenda_event(event) for event in events],
                "message": f"{len(events)} événements trouvés",
            }
        )


@app.route("/api/v2/agenda/<int:days>")
def api_agenda_day(days):
    try:
        events = ag.events_of(to=days)
    except (Exception,) as e:
        return jsonify(
            {"success": False, "data": "", "message": f"{e.__class__}: {e.args}"}
        )
    else:
        return jsonify(
            {
                "success": True,
                "data": sorted(
                    [Event.parse_agenda_event(event) for event in events],
                    key=lambda e: e.get("start"),
                ),
                "message": f"{len(events)} événements trouvés",
            }
        )


if __name__ == "__main__":
    app.run(debug=True, port=8000)
