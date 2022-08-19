from flask import Flask, send_from_directory
from flask import render_template, request
from flask.json import jsonify
from ut1ls.orm import Customer, City, Facture, ListPack, ListProduction, SubTask, PackSubTask, Pack,  db
from ut1ls.mailer import Mailer
import peewee as pw
import json
import os



app = Flask(__name__)
m = Mailer(os.getenv('EMAIL_USER', 'pdetchenou@gmail.com'))


@app.route('/')
def dashboard():
    return render_template('rwtd/dashboard.html', **{'actual' : "Tableau de bord"})

@app.route('/customers')
def customers():
    return render_template('rwtd/customers.html', **{'actual' : "Clients"})

@app.route('/packs')
def packs():
    return render_template('rwtd/packs.html', **{'actual' : "Contrats"})

@app.route('/pack/<int:pk>')
def pack(pk):
    try:
        pack : Pack = Pack.get(pk=pk)
    except (pw.DoesNotExist, ) as e:
        pass
    else:
        return render_template('rwtd/pack.html', **{'actual' : "Contrats", 'pack':pack})

@app.route('/factures')
def factures():
    return render_template('rwtd/factures.html', **{'actual' : "Factures"})

@app.route('/productions')
def productions():
    return render_template('rwtd/productions.html', **{'actual' : "Productions"})
# API endpoints

# Customer endpoints
@app.route('/api/v1/customer/create', methods=['POST',])
def api_customer_create():
    data = request.form.to_dict()
    try:
        city, _ = City.get_or_create(name=data.get('city'))
        data.update({
            'city': city.pk
        })
        data.update({'is_regulier' : True if request.form.get('is_regulier') == 'on' else False})
        data.update({'is_prospect' : True if request.form.get('is_prospect') == 'on' else False})
        c = Customer.create(**data)
    except (Exception,) as e:
        r = {
            'success': False,
            'data':'',
            'message': f'{e.__class__} : {e.args[0]}'
        }
    else:
        r = {
            'success': True,
            'data':c.serialize(),
            'message': f'Utilisateur {c.name} créé avec succès'
        }
    
    return jsonify(r)

@app.route('/api/v1/customers')
def api_customers():
    irr = request.args.get('irreguliers', type=int)
    prosp = request.args.get('prospects', type=int)
    name = request.args.get('name', '').strip()
    query : pw.ModelSelect = Customer.select()#.order_by(Customer.name.asc())
    if name:
        query = query.where(Customer.name.contains(name))
    if prosp:
        query = query.where(Customer.is_prospect == bool(prosp))
    if irr:
        query = query.where(Customer.is_regulier != bool(irr))

    cs = [c.serialize() for c in query.order_by(Customer.name.asc())]
    return jsonify({
        'success':True,
        'data':cs,
        'message':''
    })

@app.route('/api/v1/customer/<int:pk>')
def api_customer(pk):
    try:
        c : Customer = Customer.get(pk=pk)
    except (pw.DoesNotExist, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        r = {
            'success':True,
            'data':c.serialize(),
            'message':'Utilisateur trouvé'
        }
    
    return jsonify(r)

@app.route('/api/v1/customer/update/<int:pk>', methods=['POST',])
def api_customer_update(pk):
    u: Customer = Customer.get(pk=pk)
    
    data = request.form.to_dict()
    data.update({
        'city': City.get(name=request.form.get('city'))
    })
    data.update({'is_regulier' : True if request.form.get('is_regulier') == 'on' else False})
    data.update({'is_prospect' : True if request.form.get('is_prospect') == 'on' else False})
    try:
        query = Customer.update(**data).where(Customer.pk == pk)
        query.execute()
    except (Exception, ) as e:
        r = {
            'success': False,
            'data':'',
            'message': e.args[0],
        }
    else:
        u: Customer = Customer.get(pk=pk)
        r = {
            'success': True,
            'data': u.serialize(),
            'message': f'Customer {u.name} modifié'
        }
    
    return jsonify(r)

@app.route('/api/v1/customer/delete/<int:pk>', methods=['POST',])
def api_customer_delete(pk):
    try:
        c : Customer = Customer.get(pk=pk)
    except (pw.DoesNotExist, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        c.delete_instance(recursive=True)
        r = {
            'success':True,
            'data':pk,
            'message':'Utilisateur supprimé'
        }
    
    return jsonify(r)

# Packs endpoints
@app.route('/api/v1/pack/create', methods=['POST',])
def api_pack_create():
    pack :dict = json.loads(request.form.get('data'))
    
    c: Customer = Customer.get(pk=int(pack['customer']))

    with db.atomic():
        try:
            p = Pack.create(
                name=pack.get('name'),
                customer=c
            )
        except (pw.IntegrityError,) as e:
            return jsonify({
                'success': False,
                'data':'',
                'message': f'{e.__class__} : {e.args[0]}'
            })
        else:
            for sub in pack.get('subtasks'):
                s, _ = SubTask.get_or_create(
                    name=sub.get('name')
                )
                ps = PackSubTask.create(
                    subtask=s,
                    pack=p,
                    value=sub.get('value')
                )

            return jsonify({
                'success': True,
                'data': p.serialize(),
                'message': 'Pack créé avec succès'
            })

@app.route('/api/v1/packs')
def api_packs():
    soumissions = request.args.get('soumissions', type=int)
    query = Pack.select().join(Customer)
    if soumissions:
        query = query.where(Customer.is_prospect == bool(soumissions))

    ps = [p.serialize() for p in query.order_by(Pack.pk.desc())]
    return jsonify({
        'success':True,
        'data':ps,
        'message':''
    })

@app.route('/api/v1/pack/<int:pk>')
def api_pack(pk):
    try:
        p : Pack = Pack.get(pk=pk)
    except (pw.DoesNotExist, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        r = {
            'success':True,
            'data':p.serialize(),
            'message':'Pack trouvé'
        }
    
    return jsonify(r)

@app.route('/api/v1/pack/update/<int:pk>', methods=['POST'])
def api_pack_update(pk):
    try:
        pack : Pack = Pack.get(pk=pk)
    except (Exception, ) as e:
        return jsonify({
            'success':False,
            'data':'',
            'message':f'{e.args}'
        })
    else:
        pack.name = request.form.get('packName')
        pack.save()

        return jsonify({
            'success':True,
            'data':pack.serialize(),
            'message':f'Changements effectifs sur {pack.name}'
        })

@app.route('/api/v1/pack/delete/<int:pk>', methods=['POST',])
def api_pack_delete(pk):
    try:
        p : Pack = Pack.get(pk=pk)
    except (pw.DoesNotExist, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        p.delete_instance(recursive=True)
        r = {
            'success':True,
            'data':p.serialize(),
            'message':'Pack supprimé'
        }
    
    return jsonify(r)

@app.route('/api/v1/pack/facture/<int:pk>', methods=['POST',])
def api_pack_facture(pk):
    obj = request.form.get('obj')
    try:
        p : Pack = Pack.get(pk=pk)
    except (pw.DoesNotExist, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        s, f = p.generate_facture(obj)
        r = {
            'success':s,
            'data':f.serialize() if s else f,
            'message':'Pack facturé' if s else f
        }
    
    return jsonify(r)

# Subtask endpoints
@app.route('/api/v1/subtask/create', methods=['POST',])
def api_subtask_create():
    try:
        data = request.form.to_dict()
        st: SubTask = SubTask.create(**data)
    except (Exception, ) as e:
        r = {
            'success': False,
            'data':'',
            'message': f'{e.__class__} : {e.args[0]}'
        }
    else:
        r = {
            'success': True,
            'data': st.serialize(),
            'message': 'Nouveau service créé avec succès'
        }
    return jsonify(r)

@app.route('/api/v1/subtasks')
def api_subtasks():
    sts = [st.serialize() for st in SubTask.select().order_by(SubTask.name.asc())]
    return jsonify({
        'success':True,
        'data':sts,
        'message':''
    })

@app.route('/api/v1/subtask/<int:pk>')
def api_subtask(pk):
    try:
        st : SubTask = SubTask.get(pk=pk)
    except (pw.DoesNotExist, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        r = {
            'success':True,
            'data':st.serialize(),
            'message':''
        }

    return jsonify(r)

@app.route('/api/v1/subtask/delete/<int:pk>', methods=['POST',])
def api_subtask_delete(pk):
    try:
        st : SubTask = SubTask.get(pk=pk)
    except (pw.DoesNotExist, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        st.delete_instance(recursive=True)
        r = {
            'success':True,
            'data':st.serialize(),
            'message':'Service retiré'
        }

    return jsonify(r)

# Facture endpoints
@app.route('/api/v1/facture/create', methods=['POST'])
def api_facture_create():
    facture : dict = json.loads(request.form.get('data'))
    c : Customer = Customer.get(pk=int(facture.get('customer')))
    statut, f = c.generate_from_tasks(
            facture.get('obj'),
            facture.get('subtasks')
        )
    
    return jsonify({
        'success':statut,
        'data':f.serialize() if statut else f,
        'message': f'Facture {f.hash} générée' if statut else f'Erreur lors de la génération de la facture {f}'
    })

@app.route('/api/v1/factures')
def api_factures():
    soumissions = request.args.get('soumissions', type=int)
    notsent = request.args.get('notsent', type=int)
    _hash = request.args.get('hash', '').strip()

    query : pw.ModelSelect = Facture.select().join(Customer)
    if _hash:
        query = query.where(Facture.hash.contains(_hash))
    if soumissions:
        query = query.where(Customer.is_prospect == bool(soumissions))
    if notsent:
        query = query.where(Facture.sent != bool(notsent))
    fs = [f.serialize() for f in query.order_by(Facture.date.desc())]
    return jsonify({
        'success':True,
        'data':fs,
        'message':''
    })

@app.route('/api/v1/facture/<hash>')
def api_facture(hash):
    try:
        f : Facture = Facture.get(hash=hash)
    except (Exception, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        r = {
            'success':True,
            'data':f.serialize(),
            'message':'Facture'
        }
    
    return jsonify(r)

@app.route('/api/v1/facture/delete/<hash>', methods=['POST',])
def api_facture_delete(hash):
    try:
        f : Facture = Facture.get(hash=hash)
    except (pw.DoesNotExist, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        if not f.sent:
            f.delete_()
            r = {
            'success':True,
            'data':f.serialize(),
            'message':'Facture supprimé'
        }
        else:
            r = {
            'success':False,
            'data':f.serialize(),
            'message': f'La facture {f.hash} ne peut être supprimé car elle a déjà été envoyée.'
        }
    
    return jsonify(r)

@app.route('/api/v1/facture/send/<hash>', methods=['POST',])
def api_facture_send(hash):
    body = request.form.get('msg', "Message sur la facture à envoyer.")
    try:
        f : Facture = Facture.get(hash=hash)
    except (pw.DoesNotExist, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        f.send(body.strip(), m)
        r = {
            'success':True,
            'data':f.serialize(),
            'message':f'Facture {f.hash} bien envoyée à {f.customer.name}'
        }
    
    return jsonify(r)

@app.route('/api/v1/facture/view/<hash>')
def api_facture_view(hash):
    if os.path.exists(os.path.join(os.getenv('DOCS_PATH'), f'{hash}.pdf')):
        return send_from_directory(os.getenv('DOCS_PATH'), f'{hash}.pdf')
    else:
        return "Facture non disponible sur cette machine."

# Production endpoints
@app.route('/api/v1/production/create', methods=['POST'])
def api_production_create():
    name = request.form.get('list-name')
    packs = request.form.getlist('packs')
    try:
        with db.atomic():
            lp = ListProduction.create(name=name)
            for _id in packs:
                pack = Pack.get(pk=int(_id))
                ListPack.create(
                    pack=pack,
                    prod=lp
                )
    except (Exception, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        lp : ListProduction = ListProduction.get(name=name)
        r = {
            'success':True,
            'data':lp.serialize(),
            'message':'Liste de production bien crée'
        }
    return jsonify(r)

@app.route('/api/v1/productions')
def api_productions():
    ls = [lp.serialize() for lp in ListProduction.select()]
    return jsonify({
        'success':True,
        'data':ls,
        'message':''
    })

@app.route('/api/v1/production/<int:pk>')
def api_production(pk):
    try:
        prod : ListProduction = ListProduction.get(pk=pk)
    except (Exception, ) as e:
        return jsonify({
            'success':False,
            'data':'',
            'message':e.args[0]
        })
    else:
        return jsonify({
            'success':True,
            'data':prod.serialize(),
            'message':''
        })

@app.route('/api/v1/production/delete/<int:pk>', methods=['POST'])
def api_production_delete(pk):
    try:
        prod : ListProduction = ListProduction.get(pk=pk)
    except (Exception, ) as e:
        return jsonify({
            'success':False,
            'data':'',
            'message':e.args[0]
        })
    else:
        prod.delete_instance(recursive=True)
        return jsonify({
            'success':True,
            'data':prod.serialize(),
            'message':''
        })

@app.route('/api/v1/production/send/<int:pk>', methods=['POST',])
def api_production_send(pk):
    msg = request.form.get('msg', "Petit message à ajouter")
    obj = request.form.get('obj', "Objet de la facture")
    try:
        prod : ListProduction = ListProduction.get(pk=pk)
    except (Exception, ) as e:
        r = {
            'success':False,
            'data':'',
            'message':e.args[0]
        }
    else:
        packs : list[Pack] = [lp.pack for lp in ListPack.select().where(ListPack.prod == prod)]
        for pack in packs:
            try:
                statut, facture = pack.generate_facture(obj)
                facture : Facture
                if statut:
                    facture.send(msg, m)
            except (Exception, ) as e:
                return jsonify({
                    'success':False,
                    'data':pack.serialize(),
                    'message':f'Erreur {e.args[0]} au pack {pack.name}'
                })
        else:
            r = {
                'success':True,
                'data':prod.serialize(),
                'message': f'Liste de production {prod.name} facturé avec succès'
            }
    return jsonify(r)

# API Packsubtask
@app.route('/api/v1/packsubtask/create', methods=['POST',])
def api_packsubtask_create():
    pack = request.form.get('pk', type=int)
    subtask = request.form.get('subtask')
    value = request.form.get('value', type=float)
    pack = Pack.get(pk=pack)
    subtask, _ = SubTask.get_or_create(name=subtask)

    try:
        p = PackSubTask.create(
            pack=pack,
            subtask=subtask,
            value=value
        )
    except (Exception, ) as e:
        return jsonify({
            'success':False,
            'data':'',
            'message':f'{e.args}'
        })
    else:
        return jsonify({
            'success':True,
            'data':p.serialize(),
            'message':f'{p.subtask.name} ajouté au pack {p.pack.name}'
        })

@app.route('/api/v1/packsubtask/<int:pk>', methods=['POST',])
def api_packsubtask(pk):
    try:
        p = PackSubTask.get(id=pk)
    except (pw.DoesNotExist, ) as e:
        pass
    else:
        return jsonify({
            'success':True,
            'data':p.serialize(),
            'message':''
        })

@app.route('/api/v1/packsubtask/delete/<int:pk>', methods=['POST',])
def api_packsubtask_delete(pk):
    try:
        p : PackSubTask = PackSubTask.get(id=pk)
    except (pw.DoesNotExist, ) as e:
        pass
    else:
        p.delete_instance()
        return jsonify({
            'success':True,
            'data':p.serialize(),
            'message':f'{p.subtask.name} retiré du pack {p.pack.name}'
        })

# Utilitaires endpoints
@app.route('/api/v2/backup', methods=['POST',])
def backup():
    instance = request.form.get('instance')
    file = request.files.get('toload')
    with file.stream as f:
        print(f.read().decode(errors='ignore'))
    return jsonify({
        'success':True,
        'data':'',
        'message':'Données chargées'
    })


if __name__ == '__main__':
    app.run(debug=True, port=8000)
