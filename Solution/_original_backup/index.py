from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlalchemy as db
import os
from werkzeug.utils import secure_filename
import datetime


engine          = db.create_engine("mysql+mysqlconnector://root:@localhost/medicalappointmentsfinal")
connection      = engine.connect()

app = Flask(__name__)
app.secret_key   = 'FinalProject'


app.config['UPLOAD_FOLDER'] = 'static/images/'


@app.route('/', methods=['GET', 'POST'])
def index():
    metadata     = db.MetaData()
    hospitals    = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)

    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        if search_query:
            query = db.select([hospitals]).where(hospitals.c.name.ilike(f"%{search_query}%") | hospitals.c.city.ilike(f"%{search_query}%"))
        else:
            query = db.select([hospitals])
    else:
        query = db.select([hospitals])
    
    result_proxy = connection.execute(query)
    result       = result_proxy.fetchall()

    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        return render_template('index.html', result=result, user_id=user_id, user_role=user_role)
    else:
        return render_template('index.html', result=result)




@app.route('/fdoctors', methods=['GET', 'POST'])    
def fdoctors():
    metadata            = db.MetaData()
    doctors             = db.Table('doctors', metadata, autoload=True, autoload_with=engine)
  

    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        if search_query:
            query = db.select([doctors]).where(doctors.c.name.like('%' + search_query + '%') | doctors.c.specialization.like('%' + search_query + '%') | doctors.c.description.like('%' + search_query + '%'))
        else:
            query = db.select([doctors])
    else:
        query = db.select([doctors])

    result_proxy        = connection.execute(query)
    result              = result_proxy.fetchall()
    data = []
    for i in result: 
        id          = i[0]
        name        = i[1]
        hospital_id = i[2]
        
        hospitals   = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
        query       = db.select([hospitals]).where(hospitals.c.id == hospital_id)
        result_proxy= connection.execute(query)
        hospital    = result_proxy.fetchall()
        count      = len(hospital)
        if count > 0:
            hospital_name = hospital[0][1]
        else:
            hospital_name = 'Not Found'
        
        specialization  = i[3]
        fee             = i[4]
        slots           = i[5]
        image           = i[7]
        description     = i[6]
        data.append([id, name, hospital_name, specialization, fee, slots, image, description])

    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']    
        return render_template('fdoctors.html', result=data, user_id=user_id, user_role=user_role)
    else:
        return render_template('fdoctors.html', result=data)






@app.route('/ffacilities', methods=['GET', 'POST'])
def ffacilities():
    metadata = db.MetaData()
    facilities = db.Table('facilities', metadata, autoload=True, autoload_with=engine)
    hospitals = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
        

    if request.method == 'POST':
        search_query = request.form.get('search_query', '').strip()
        if search_query:
            query = db.select([facilities]).where(facilities.c.name.like('%' + search_query + '%') | facilities.c.services.like('%' + search_query + '%') | facilities.c.description.like('%' + search_query + '%'))
        else:
            query = db.select([facilities])
    else:
        query = db.select([facilities])



    result_proxy = connection.execute(query)
    result = result_proxy.fetchall()
    data = []
    for row in result:
        facility_id = row[0]
        name = row[2]
        hospital_id = row[1]

        query = db.select([hospitals.c.name]).where(hospitals.c.id == hospital_id)
        result_proxy = connection.execute(query)
        hospital_name = result_proxy.scalar()

        description = row[3]
        services = row[4]
        fee = row[5]
        contact = row[6]

        data.append([facility_id, name, hospital_name, description, services, fee, contact])

    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        return render_template('ffacilities.html', result=data, user_id=user_id, user_role=user_role)
    else:
        return render_template('ffacilities.html', result=data)









@app.route('/login', methods=['GET', 'POST'])
def sign_in():
    metadata        = db.MetaData()
    users           = db.Table('users', metadata, autoload=True, autoload_with=engine)
    if request.method == 'POST':
        email            = request.form['email']
        password         = request.form['password']
    
        query            = db.select([users]).where(db.and_(users.c.email == email, users.c.password ==  password))
        result_proxy     = connection.execute(query)
        result           = result_proxy.fetchall()
        count            = len(result)
        if count > 0: 
            row             = result[0]
            user_id         = row.id
            user_role       = row.role
            session['id']   = user_id
            session['role'] = user_role
            return redirect(url_for('account'))  
        else:
            message = 'Email or Password is Incorrect.'

        return render_template('login.html', message=message)
    return render_template('login.html')


@app.route('/register', methods=['GET','POST'])
def sign_up():
    metadata        = db.MetaData()
    users           = db.Table('users', metadata, autoload=True, autoload_with=engine)
    if request.method == 'POST':
        email            = request.form['email']
        query            = db.select([users]).where(users.c.email == email)
        result_proxy     = connection.execute(query)
        searchrows       = result_proxy.fetchall()
        count            = len(searchrows)
        if count > 0:
            message = 'This Email Is Already In Use'
        else:
            name        = request.form['name']
            password    = request.form['password']
            phone       = request.form['phone']
            city        = request.form['city']
            role        = request.form['role']
            query       = db.insert(users).values(name=name, email=email, password=password, phone=phone, city=city, role=role)
            connection.execute(query)
            message         = 'Congrats, Your Account Is Created'
        return render_template('register.html', message=message)
    return render_template('register.html')


@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        metadata            = db.MetaData()
        users               = db.Table('users', metadata, autoload=True, autoload_with=engine)
        query               = db.select([users]).where(users.c.id == user_id)
        result_proxy        = connection.execute(query)
        row                 = result_proxy.first()
        return render_template('account.html', id=user_id, role=user_role, row=row)
    else:
        return redirect(url_for('logout'))


@app.route('/addhospital', methods=['GET', 'POST'])
def addhospital():
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        if user_role == 'admin':
            metadata            = db.MetaData()
            hospitals           = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
            if request.method == 'POST':
                name        = request.form['name']
                city        = request.form['city']
                address     = request.form['address']
                phone       = request.form['phone']
                description = request.form['description']
                
                
                image       = request.files['image']
                image_name  = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))
    
                query       = db.select([hospitals]).where(hospitals.c.name == name)
                result_proxy= connection.execute(query)
                searchrows  = result_proxy.fetchall()
                count       = len(searchrows)
                if count > 0:
                    message = 'This Hospital Is Already Added'
                    return render_template('addhospital.html', id=user_id, role=user_role, message=message)
                else:
                    query       = db.insert(hospitals).values(name=name, address=address, phone=phone, city=city, description=description, image=image_name)
                    connection.execute(query)
                    message         = 'Congrats, Hospital Is Added'
                    return render_template('addhospital.html', id=user_id, role=user_role, message=message)
            return render_template('addhospital.html', id=user_id, role=user_role)
        else:
            return redirect(url_for('logout'))
    else:
        return redirect(url_for('logout'))



@app.route('/addfacility', methods=['GET', 'POST'])
def addfacility():
    if 'id' in session and 'role' in session:
        user_id = session['id']
        user_role = session['role']
        if user_role == 'admin':
            metadata = db.MetaData()
            hospitals = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
            facilities = db.Table('facilities', metadata, autoload=True, autoload_with=engine)

            message = None  

            if request.method == 'POST':
                
                hospital_id = request.form.get('hospital_id')
                name        = request.form.get('name')
                description = request.form.get('description')
                services    = request.form.get('services')
                fee         = request.form.get('fee')
                contact     = request.form.get('contact')

                
                sel = db.select([facilities]).where(facilities.c.hospital_id == hospital_id, facilities.c.name == name)
                result_proxy = connection.execute(sel)
                existing_facility = result_proxy.fetchone()

                if existing_facility:
                    message = "Facility already exists in the same hospital."
                else:
                    # Add the facility to the database
                    ins = facilities.insert().values(hospital_id=hospital_id, name=name, description=description, services=services, fee=fee, contact=contact)
                    connection.execute(ins)
                    message = "Facility added successfully!"

            
            sel = db.select([hospitals])
            result_proxy = connection.execute(sel)
            hospitals = result_proxy.fetchall()

            return render_template('addfacility.html', id=user_id, role=user_role, hospitals=hospitals, message=message)
        else:
            return redirect(url_for('logout'))
    else:
        return redirect(url_for('logout'))





@app.route('/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        if user_role == 'admin':
            metadata            = db.MetaData()
            doctors             = db.Table('doctors', metadata, autoload=True, autoload_with=engine)

            hospitals           = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
            query               = db.select([hospitals])
            result_proxy        = connection.execute(query)
            hospitals           = result_proxy.fetchall()

            if request.method == 'POST':
                name           = request.form['name']
                specialization = request.form['specialization']
                fee            = request.form['fee']
                slots          = request.form['slots']
                hospital_id    = request.form['hospital_id']
                description   = request.form['description']
                image          = request.files['image']
                image_name     = secure_filename(image.filename)
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], image_name))

                
                query       = db.select([doctors]).where(db.and_(doctors.c.name == name, doctors.c.hospital_id == hospital_id))
                result_proxy= connection.execute(query)
                searchrows  = result_proxy.fetchall()
                count       = len(searchrows)
                if count > 0:
                    message = 'This Doctor Is Already Added'
                    return render_template('add_doctor.html', id=user_id, role=user_role, message=message, hospitals=hospitals)
                else:
                    query       = db.insert(doctors).values(name=name, specialization=specialization, fee=fee, slots=slots, hospital_id=hospital_id, description=description, image=image_name)
                    connection.execute(query)
                    message         = 'Congrats, Your Doctor Is Added'
                    return render_template('add_doctor.html', id=user_id, role=user_role, message=message, hospitals=hospitals)
            return render_template('add_doctor.html', id=user_id, role=user_role, hospitals=hospitals)
        else:
            return redirect(url_for('logout'))
    else:
        return redirect(url_for('logout'))



@app.route('/hospitals', methods=['GET', 'POST'])
def hospitals():
    if 'id' in session and 'role' in session:

        user_id   = session['id']
        user_role = session['role']
        metadata  = db.MetaData()
        hospitals = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)

        if request.method == 'POST':
            search_query = request.form.get('hospital_name', '').strip()
            if search_query:
                query = db.select([hospitals]).where(hospitals.c.name.ilike(f"%{search_query}%"))
            else:
                query = db.select([hospitals])
        else:
            query = db.select([hospitals])

        result_proxy = connection.execute(query)
        result = result_proxy.fetchall()

        if user_role == 'admin':
            return render_template('hospitals.html', id=user_id, role=user_role, result=result)
        else:
            return render_template('user_hospitals.html', id=user_id, role=user_role, result=result)
    else:
        return redirect(url_for('logout'))





@app.route('/doctors', methods=['GET', 'POST'])
def doctors():
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        metadata            = db.MetaData()
        doctors             = db.Table('doctors', metadata, autoload=True, autoload_with=engine)

        
    
        
        if request.method == 'POST':
            search_query = request.form.get('search_query', '').strip()
            if search_query:
                query = db.select([doctors]).where(doctors.c.name.like('%' + search_query + '%') | doctors.c.specialization.like('%' + search_query + '%') | doctors.c.description.like('%' + search_query + '%'))
            else:
                query = db.select([doctors])
        else:
            query = db.select([doctors])
        
        
        result_proxy        = connection.execute(query)
        result              = result_proxy.fetchall()
        data = []
        for i in result:
            id          = i[0]
            name        = i[1]
            hospital_id = i[2]
            
            hospitals   = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
            query       = db.select([hospitals]).where(hospitals.c.id == hospital_id)
            result_proxy= connection.execute(query)
            hospital    = result_proxy.fetchall()
            count      = len(hospital)
            if count > 0:
                hospital_name = hospital[0][1]
            else:
                hospital_name = 'Not Found'
            
            specialization  = i[3]
            fee             = i[4]
            slots           = i[5]
            image           = i[7]
            data.append([id, name, hospital_name, specialization, fee, slots, image])

        
        return render_template('doctors.html', id=user_id, role=user_role, result=data)
        
    else:
        return redirect(url_for('logout'))
    


@app.route('/users', methods=['GET', 'POST'])
def users():
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        metadata            = db.MetaData()
        users             = db.Table('users', metadata, autoload=True, autoload_with=engine)

    
        if request.method == 'POST':
            search_query = request.form.get('search_query', '').strip()
            if search_query:          
                query = db.select([users]).where(db.and_(users.c.role == 'user', db.or_(users.c.name.like('%' + search_query + '%'), users.c.email == search_query, users.c.city == search_query)))
            else:
                
                query = db.select([users]).where(users.c.role == 'user')
                
        else:
            query = db.select([users]).where(users.c.role == 'user')
        
        
        result_proxy        = connection.execute(query)
        result              = result_proxy.fetchall()
        
        return render_template('users.html', id=user_id, role=user_role, result=result)
        
    else:
        return redirect(url_for('logout'))



@app.route('/user_edit/<int:id>', methods=['GET', 'POST'])
def user_edit(id):
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        metadata            = db.MetaData()
        users               = db.Table('users', metadata, autoload=True, autoload_with=engine)

        query               = db.select([users]).where(users.c.id == id)
        result_proxy        = connection.execute(query)
        result              = result_proxy.first()

        if request.method == 'POST':
            name            = request.form.get('name', '').strip()
            email           = request.form.get('email', '').strip()
            city            = request.form.get('city', '').strip()
            password        = request.form.get('password', '').strip()
            phone           = request.form.get('phone', '').strip()
            
            if name and email and city and password and phone:
                query = db.update(users).values(name=name, email=email, city=city, password=password, phone=phone).where(users.c.id == id)
                connection.execute(query)
                message         = 'Congrats, Your User Is Updated'
                
                query               = db.select([users]).where(users.c.id == id)
                result_proxy        = connection.execute(query)
                result              = result_proxy.first()
                return render_template('user_edit.html', id=user_id, role=user_role, message=message, row=result)
            else:
                message         = 'Please Fill All The Fields'
                return render_template('user_edit.html', id=user_id, role=user_role, message=message, row=result)
        


        else:
            return render_template('user_edit.html', id=user_id, role=user_role, row=result)
    else:
        return redirect(url_for('logout'))
    


@app.route('/setting', methods=['GET', 'POST'])
def setting():
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        metadata            = db.MetaData()
        users               = db.Table('users', metadata, autoload=True, autoload_with=engine)

        query               = db.select([users]).where(users.c.id == user_id)
        result_proxy        = connection.execute(query)
        result              = result_proxy.first()

        if request.method == 'POST':
            name            = request.form.get('name', '').strip()
            email           = request.form.get('email', '').strip()
            city            = request.form.get('city', '').strip()
            password        = request.form.get('password', '').strip()
            phone           = request.form.get('phone', '').strip()
            
            if name and email and city and password and phone:
                query = db.update(users).values(name=name, email=email, city=city, password=password, phone=phone).where(users.c.id == user_id)
                connection.execute(query)
                message         = 'Congrats, Your Profile Is Updated'
                
                query               = db.select([users]).where(users.c.id == user_id)
                result_proxy        = connection.execute(query)
                result              = result_proxy.first()
                return render_template('setting.html', id=user_id, role=user_role, message=message, row=result)
            else:
                message         = 'Please Fill All The Fields'
                return render_template('setting.html', id=user_id, role=user_role, message=message, row=result)
        
        else:
            return render_template('setting.html', id=user_id, role=user_role, row=result)
    else:
        return redirect(url_for('logout'))


@app.route('/user_delete/<int:id>', methods=['GET', 'POST'])
def user_delete(id):
    if 'id' in session and 'role' in session:
        metadata            = db.MetaData()
        users               = db.Table('users', metadata, autoload=True, autoload_with=engine)

        query = db.delete(users).where(users.c.id == id)
        result_proxy = connection.execute(query)
        return redirect(url_for('users'))
    else:
        return redirect(url_for('logout'))
    









@app.route('/detail/<int:id>', methods=['GET', 'POST'])
def detail(id):
    metadata            = db.MetaData()
    hospitals           = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
    query               = db.select([hospitals]).where(hospitals.c.id == id)
    result_proxy        = connection.execute(query)
    result              = result_proxy.first()

    # doctors
    doctors              = db.Table('doctors', metadata, autoload=True, autoload_with=engine)
    dquery               = db.select([doctors]).where(doctors.c.hospital_id == id)
    dresult_proxy        = connection.execute(dquery)
    dresult              = dresult_proxy.fetchall()

    data = []
    for i in dresult:
        id          = i[0]
        name        = i[1]
        hospital_id = i[2]
        
        squery       = db.select([hospitals]).where(hospitals.c.id == hospital_id)
        sresult_proxy= connection.execute(squery)
        shospital    = sresult_proxy.fetchall()
        count      = len(shospital)
        if count > 0:
            hospital_name = shospital[0][1]
        else:
            hospital_name = 'Not Found'
        
        specialization  = i[3]
        fee             = i[4]
        slots           = i[5]
        image           = i[7]
        description     = i[6]
        data.append([id, name, hospital_name, specialization, fee, slots, image, description])

    
    # facilities
    
    facilities = db.Table('facilities', metadata, autoload=True, autoload_with=engine)
    

    fquery        = db.select([facilities]).where(facilities.c.hospital_id == id)
    fresult_proxy = connection.execute(fquery)
    fresult       = fresult_proxy.fetchall()
    fdata = []
    for row in fresult:
        facility_id = row[0]
        name        = row[2]
        hospital_id = row[1]

        ssquery = db.select([hospitals.c.name]).where(hospitals.c.id == hospital_id)
        ssresult_proxy = connection.execute(ssquery)
        hospital_name = ssresult_proxy.scalar()

        description = row[3]
        services    = row[4]
        fee         = row[5]
        contact     = row[6]

        fdata.append([facility_id, name, hospital_name, description, services, fee, contact])

    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        return render_template('detail.html', result=result, doctors=data, facilities=fdata, user_id=user_id, user_role=user_role)
    else:
        return render_template('detail.html', result=result, doctors=data, facilities=fdata)





@app.route('/book_doctor/<int:id>', methods=['GET', 'POST'])
def book_doctor(id):
    metadata            = db.MetaData()
    doctors              = db.Table('doctors', metadata, autoload=True, autoload_with=engine)
    hospitals           = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
    dquery               = db.select([doctors]).where(doctors.c.id == id)
    dresult_proxy        = connection.execute(dquery)
    dresult              = dresult_proxy.fetchall()

    data = []
    for i in dresult:
        id          = i[0]
        name        = i[1]
        hospital_id = i[2]
        
        squery       = db.select([hospitals]).where(hospitals.c.id == hospital_id)
        sresult_proxy= connection.execute(squery)
        shospital    = sresult_proxy.fetchall()
        count      = len(shospital)
        if count > 0:
            hospital_name = shospital[0][1]
        else:
            hospital_name = 'Not Found'
        
        specialization  = i[3]
        fee             = i[4]
        slots           = i[5]
        image           = i[7]
        description     = i[6]
        data.append([id, name, hospital_name, specialization, fee, slots, image, description])

        today = datetime.datetime.today().strftime('%Y-%m-%d')
        
    # save booking
    if request.method == 'POST':
        doctor = request.form['doctor_id']
        user   = request.form['user_id']
        date   = request.form['date']
        slot   = request.form['slot']

        # check if someone already booked on this date and slot with this doctor
        bookings = db.Table('doctor_bookings', metadata, autoload=True, autoload_with=engine)
        bquery   = db.select([bookings]).where(db.and_(bookings.c.doctor_id == doctor, bookings.c.date == date, bookings.c.slot == slot))
        bresult_proxy = connection.execute(bquery)
        bresult       = bresult_proxy.fetchall()
        count         = len(bresult)
        if count > 0:
            flash('Someone already booked on this date and slot with this doctor')
            return redirect(url_for('book_doctor', id=doctor))
        else:
            # now check if user is already booked with this doctor on same date and slot
            bquery   = db.select([bookings]).where(db.and_(bookings.c.user_id == user, bookings.c.date == date, bookings.c.slot == slot, bookings.c.doctor_id == doctor))
            bresult_proxy = connection.execute(bquery)
            bresult       = bresult_proxy.fetchall()
            count         = len(bresult)
            if count > 0:
                flash('You already booked with this doctor on same date and slot')
                return redirect(url_for('book_doctor', id=doctor))
            else:
                # now save booking
                query = db.insert(bookings).values(doctor_id=doctor, user_id=user, date=date, slot=slot)
                result_proxy = connection.execute(query)
                flash('Booking Successful')
                return redirect(url_for('book_doctor', id=doctor))




    if 'id' in session and 'role' in session:
        user_id = session['id']
        user_role = session['role']
        return render_template('book_doctor.html', result=data, doctor_id=id, user_id=user_id, user_role=user_role, today=today)
    else:
        return render_template('book_doctor.html', result=data, doctor_id=id, today=today)
    



@app.route('/docbookings/<int:id>', methods=['GET', 'POST'])
def docbookings(id):
    if 'id' in session and 'role' in session: 
        user_id   = session['id']
        user_role = session['role']
        metadata  = db.MetaData()
        doctors   = db.Table('doctors', metadata, autoload=True, autoload_with=engine)
        bookings  = db.Table('doctor_bookings', metadata, autoload=True, autoload_with=engine)
        users     = db.Table('users', metadata, autoload=True, autoload_with=engine)
        
        query     = db.select([bookings]).where(bookings.c.doctor_id == id)
        result_proxy = connection.execute(query)
        result       = result_proxy.fetchall()

        data = []
        for i in result:
            id         = i[0]
            doctor_id  = i[1]
            dquery     = db.select([doctors]).where(doctors.c.id == doctor_id)
            dresult_proxy = connection.execute(dquery)
            dresult       = dresult_proxy.fetchall()
            dcount         = len(dresult)
            if dcount > 0:
                doctor_name = dresult[0][1]
            else:
                doctor_name = '-'
            user_id    = i[2]
            
            uquery     = db.select([users]).where(users.c.id == user_id)
            uresult_proxy = connection.execute(uquery)
            uresult       = uresult_proxy.fetchall()
            count         = len(uresult)
            if count > 0:
                username = uresult[0][1]
            else:
                username = '-'
            date       = i[3]
            date       = date.strftime('%d %B, %Y')
            slot       = i[4]
            data.append([id, doctor_name, username, date, slot])

        return render_template('docbookings.html', result=data, user_id=user_id, user_role=user_role)
    
    else:
        return redirect(url_for('logout'))


@app.route('/del_docbookings/<int:id>', methods=['GET', 'POST'])
def del_docbookings(id):
    if 'id' in session and 'role' in session: 
        metadata  = db.MetaData()
        bookings  = db.Table('doctor_bookings', metadata, autoload=True, autoload_with=engine)
        squery        = db.select([bookings]).where(bookings.c.id == id)
        sresult_proxy = connection.execute(squery)
        sresult       = sresult_proxy.fetchall()
        doctor_id     = sresult[0][1]

        query     = db.delete(bookings).where(bookings.c.id == id)
        connection.execute(query)
        return redirect(url_for('docbookings', id=doctor_id))
    else:
        return redirect(url_for('logout'))
    



@app.route('/facbookings/<int:id>', methods=['GET', 'POST'])
def facbookings(id):
    if 'id' in session and 'role' in session: 
        user_id   = session['id']
        user_role = session['role']
        metadata  = db.MetaData()
    
        bookings  = db.Table('facility_bookings', metadata, autoload=True, autoload_with=engine)
        users     = db.Table('users', metadata, autoload=True, autoload_with=engine)
        
        query     = db.select([bookings]).where(bookings.c.facility_id == id)
        result_proxy = connection.execute(query)
        result       = result_proxy.fetchall()

        data = []
        for i in result:
            id         = i[0]
            user_id    = i[2]
            
            uquery     = db.select([users]).where(users.c.id == user_id)
            uresult_proxy = connection.execute(uquery)
            uresult       = uresult_proxy.fetchall()
            count         = len(uresult)
            if count > 0:
                username = uresult[0][1]
            else:
                username = '-'
            
            service    = i[3]
            image      = i[4]

            date       = i[5]
            date       = date.strftime('%d %B, %Y')
            result     = i[6]
            status     = i[7]

            data.append([id, username, service, image, date, result, status])
        return render_template('facilitybookings.html', result=data, user_id=user_id, user_role=user_role)
    else:
        return redirect(url_for('logout'))



@app.route('/del_facbookings/<int:id>', methods=['GET', 'POST'])
def del_facbookings(id):
    if 'id' in session and 'role' in session: 
        metadata  = db.MetaData()
        bookings  = db.Table('facility_bookings', metadata, autoload=True, autoload_with=engine)
        squery        = db.select([bookings]).where(bookings.c.id == id)
        sresult_proxy = connection.execute(squery)
        sresult       = sresult_proxy.fetchall()
        facility_id     = sresult[0][1]

        query     = db.delete(bookings).where(bookings.c.id == id)
        connection.execute(query)
        return redirect(url_for('facbookings', id=facility_id))
    else:
        return redirect(url_for('logout'))
    



@app.route('/user_docbookings', methods=['GET', 'POST'])
def user_docbookings():
    if 'id' in session and 'role' in session: 
        user_id   = session['id']
        user_role = session['role']
        metadata  = db.MetaData()
    
        bookings  = db.Table('doctor_bookings', metadata, autoload=True, autoload_with=engine)
        doctors   = db.Table('doctors', metadata, autoload=True, autoload_with=engine)
        
        query     = db.select([bookings]).where(bookings.c.user_id == user_id)
        result_proxy = connection.execute(query)
        result       = result_proxy.fetchall()

        data = []
        for i in result:
            id         = i[0]
            doctor_id  = i[1]
            dquery     = db.select([doctors]).where(doctors.c.id == doctor_id)
            dresult_proxy = connection.execute(dquery)
            dresult       = dresult_proxy.fetchall()
            dcount         = len(dresult)
            if dcount > 0:
                doctor_name = dresult[0][1]
            else:
                doctor_name = '-'
            date       = i[3]
            date       = date.strftime('%d %B, %Y')
            slot       = i[4]
            data.append([id, doctor_name, date, slot])

        return render_template('userdocbookings.html', result=data, user_id=user_id, user_role=user_role)
    
    else:
        return redirect(url_for('logout'))




@app.route('/deluser_docbookings/<int:id>', methods=['GET', 'POST'])
def deluser_docbookings(id):
    if 'id' in session and 'role' in session: 
        metadata  = db.MetaData()
        bookings  = db.Table('doctor_bookings', metadata, autoload=True, autoload_with=engine)
        query     = db.delete(bookings).where(bookings.c.id == id)
        connection.execute(query)
        return redirect(url_for('user_docbookings'))
    else:
        return redirect(url_for('logout'))



@app.route('/user_facbookings', methods=['GET', 'POST'])
def user_facbookings():
    if 'id' in session and 'role' in session: 
        user_id   = session['id']
        user_role = session['role']
        metadata  = db.MetaData()
    
        bookings  = db.Table('facility_bookings', metadata, autoload=True, autoload_with=engine)
        facilities   = db.Table('facilities', metadata, autoload=True, autoload_with=engine)
        
        query     = db.select([bookings]).where(bookings.c.user_id == user_id)
        result_proxy = connection.execute(query)
        result       = result_proxy.fetchall()

        data = []
        for i in result:
            id          = i[0]
            facility_id = i[1]
            
            
            fquery     = db.select([facilities]).where(facilities.c.id == facility_id) 
            fresult_proxy = connection.execute(fquery)
            fresult       = fresult_proxy.fetchall()
            fcount         = len(fresult)
            if fcount > 0:
                facility_name = fresult[0][2]
            else:
                facility_name = '-'
            
            date       = i[5]
            date       = date.strftime('%d %B, %Y')
            service    = i[3]
            image      = i[4]
            result     = i[6]
            status     = i[7]
            data.append([id, facility_name, date, service, image, result, status])
        return render_template('userfacbookings.html', result=data, user_id=user_id, user_role=user_role)
    
    else:
        return redirect(url_for('logout'))




@app.route('/res_positive/<int:id>', methods=['GET', 'POST'])
def res_positive(id):
    if 'id' in session and 'role' in session: 
        metadata  = db.MetaData()
        bookings  = db.Table('facility_bookings', metadata, autoload=True, autoload_with=engine)
        squery        = db.select([bookings]).where(bookings.c.id == id)
        sresult_proxy = connection.execute(squery)
        sresult       = sresult_proxy.fetchall()
        facility_id     = sresult[0][1]

        query     = db.update(bookings).values(status=1, result='Positive').where(bookings.c.id == id)
        connection.execute(query)
        return redirect(url_for('facbookings', id=facility_id))
    else:
        return redirect(url_for('logout'))


@app.route('/res_negitive/<int:id>', methods=['GET', 'POST'])
def res_negitive(id):
    if 'id' in session and 'role' in session: 
        metadata  = db.MetaData()
        bookings  = db.Table('facility_bookings', metadata, autoload=True, autoload_with=engine)
        squery        = db.select([bookings]).where(bookings.c.id == id)
        sresult_proxy = connection.execute(squery)
        sresult       = sresult_proxy.fetchall()
        facility_id     = sresult[0][1]

        query     = db.update(bookings).values(status=1, result='Negitive').where(bookings.c.id == id)
        connection.execute(query)
        return redirect(url_for('facbookings', id=facility_id))
    else:
        return redirect(url_for('logout'))





@app.route('/book_facilities/<int:id>', methods=['GET', 'POST'])
def book_facilities(id):
    metadata            = db.MetaData()
    facilities          = db.Table('facilities', metadata, autoload=True, autoload_with=engine)
    hospitals           = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
    dquery              = db.select([facilities]).where(facilities.c.id == id)
    dresult_proxy       = connection.execute(dquery)
    dresult             = dresult_proxy.fetchall()

    data = []
    for i in dresult:
        id          = i[0]
        name        = i[2]
        hospital_id = i[1]
        
        squery       = db.select([hospitals]).where(hospitals.c.id == hospital_id)
        sresult_proxy= connection.execute(squery)
        shospital    = sresult_proxy.fetchall()
        count      = len(shospital)
        if count > 0:
            hospital_name = shospital[0][1]
        else:
            hospital_name = 'Not Found'
        
        description = i[3]
        services    = i[4]
        fee         = i[5]
        contact     = i[6]
        
        data.append([id, name, hospital_name, description, services, fee, contact])

        today = datetime.datetime.today().strftime('%Y-%m-%d')
        
    # save booking
    if request.method == 'POST':
        facility = request.form['facility_id']
        user    = request.form['user_id']
        date    = request.form['date']
        service = request.form['service']

        # image
        image = request.files['image']
        filename = secure_filename(image.filename)
        image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        
        bookings = db.Table('facility_bookings', metadata, autoload=True, autoload_with=engine)
        # check if user already booked with this facility and service and status is 0
        bquery   = db.select([bookings]).where(db.and_(bookings.c.user_id == user, bookings.c.facility_id == facility, bookings.c.service == service, bookings.c.status == 0))
        bresult_proxy = connection.execute(bquery)
        bresult       = bresult_proxy.fetchall()
        count         = len(bresult)
        if count > 0:
            flash('You already booked the service with this facility, wait for result')
            return redirect(url_for('book_facilities', id=facility))
        else:
            # now save booking
            query = db.insert(bookings).values(facility_id=facility, user_id=user, service=service, image=filename, date=date)
            result_proxy = connection.execute(query)
            flash('Service Booking Successful')
            return redirect(url_for('book_facilities', id=facility))



    if 'id' in session and 'role' in session:
        user_id = session['id']
        user_role = session['role']
        return render_template('book_facilities.html', result=data, facility_id=id, user_id=user_id, user_role=user_role, today=today)
    else:
        return render_template('book_facilities.html', result=data, facility_id=id, today=today)





@app.route('/facilities', methods=['GET', 'POST'])
def facilities():
    if 'id' in session and 'role' in session:
        user_id = session['id']
        user_role = session['role']
        metadata = db.MetaData()
        facilities = db.Table('facilities', metadata, autoload=True, autoload_with=engine)
        hospitals = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)

        if request.method == 'POST':
            search_query = request.form.get('search_query', '').strip()
            if search_query:
                query = db.select([facilities]).where(facilities.c.name.like('%' + search_query + '%') | facilities.c.services.like('%' + search_query + '%') | facilities.c.description.like('%' + search_query + '%'))
            else:
                query = db.select([facilities])
        else:
            query = db.select([facilities])

        result_proxy = connection.execute(query)
        result = result_proxy.fetchall()
        data = []
        for row in result:
            facility_id = row[0]
            name = row[2]
            hospital_id = row[1]

            query = db.select([hospitals.c.name]).where(hospitals.c.id == hospital_id)
            result_proxy = connection.execute(query)
            hospital_name = result_proxy.scalar()

            description = row[3]
            services = row[4]
            fee = row[5]
            contact = row[6]

            data.append([facility_id, name, hospital_name, description, services, fee, contact])

        if user_role == 'admin':
            return render_template('facilities.html', id=user_id, role=user_role, result=data)
        else:
            return render_template('user_facilities.html', id=user_id, role=user_role, result=data)
    else:
        return redirect(url_for('logout'))





@app.route('/hospitals/delete/<int:id>', methods=['GET', 'POST'])
def hospital_delete(id):
    if 'id' in session and 'role' in session:
        user_role           = session['role']
        if user_role == 'admin':
            metadata            = db.MetaData()
            hospitals           = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
            query               = db.delete(hospitals).where(hospitals.c.id==id)
            connection.execute(query)
            return redirect(url_for('hospitals'))
        else:
            return redirect(url_for('logout'))
    else:
        return redirect(url_for('logout'))
    

@app.route('/doctors/delete/<int:id>', methods=['GET', 'POST'])
def doctor_delete(id):
    if 'id' in session and 'role' in session:
        user_role           = session['role']
        if user_role == 'admin':
            metadata            = db.MetaData()
            doctors             = db.Table('doctors', metadata, autoload=True, autoload_with=engine)
            query               = db.delete(doctors).where(doctors.c.id==id)
            connection.execute(query)
            return redirect(url_for('doctors'))
        else:
            return redirect(url_for('logout'))
    else:
        return redirect(url_for('logout'))
    


@app.route('/facilities/delete/<int:id>', methods=['GET', 'POST'])
def facility_delete(id):
    if 'id' in session and 'role' in session:
        user_role           = session['role']
        if user_role == 'admin':
            metadata            = db.MetaData()
            facilities          = db.Table('facilities', metadata, autoload=True, autoload_with=engine)
            query               = db.delete(facilities).where(facilities.c.id==id)
            connection.execute(query)
            return redirect(url_for('facilities'))
        else:
            return redirect(url_for('logout'))
    else:
        return redirect(url_for('logout'))


@app.route('/hospitals/edit/<int:id>', methods=['GET', 'POST'])
def hospital_edit(id):
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        hospital_id        = id
        if user_role == 'admin':
            metadata            = db.MetaData()
            hospitals           = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
            query               = db.select([hospitals]).where(hospitals.c.id == id)
            result_proxy        = connection.execute(query)
            result              = result_proxy.fetchall()
            if request.method == 'POST':
                hid         = request.form['hid']
                name        = request.form['name']
                city        = request.form['city']
                address     = request.form['address']
                phone       = request.form['phone']
                description = request.form['description']
                old_image   = request.form['old_image']

                # check if image is uploaded, if uplodaded then save it otherwise use old image
                if 'image' in request.files:
                    image       = request.files['image']
                    filename    = secure_filename(image.filename)
                    # use static/images folder to save image
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_name  = filename
                else:
                    image_name  = old_image

                query       = db.update(hospitals).where(hospitals.c.id == hid).values(name=name, address=address, phone=phone, city=city, description=description, image=image_name)
                connection.execute(query)
                updateInfo           = db.select([hospitals]).where(hospitals.c.id == hid)
                update_result        = connection.execute(updateInfo)
                update_row           = update_result.first()
                return render_template('hospital_edit.html', id=user_id, role=user_role, row=update_row, hospital_id=id, update='Hospital Info is Updated') 
            else:
                count               = len(result)
                if count < 1:
                    return render_template('hospital_edit.html', id=user_id, role=user_role, result=result, message='Hospital Not Found', hospital_id=id)
                else:
                    row             = result[0]
                    return render_template('hospital_edit.html', id=user_id, role=user_role, row=row, hospital_id=id)           
        else:
            return redirect(url_for('logout'))

    else:
        return redirect(url_for('logout'))
    



@app.route('/facilities/edit/<int:id>', methods=['GET', 'POST'])
def facility_edit(id):
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        facility_id         = id
        if user_role == 'admin':
            metadata            = db.MetaData()
            facilities             = db.Table('facilities', metadata, autoload=True, autoload_with=engine)
            query               = db.select([facilities]).where(facilities.c.id == id)
            result_proxy        = connection.execute(query)
            result              = result_proxy.fetchall()

            # hospitals
            hospitals           = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
            hospital_query      = db.select([hospitals])
            hospital_result     = connection.execute(hospital_query)
            hospitals       = hospital_result.fetchall()
            if request.method == 'POST':
                fid            = request.form['fid']
                name           = request.form['name']
                hospital_id    = request.form['hospital_id']
                description = request.form['description']
                fee            = request.form['fee']
                services          = request.form['services']
                contact        = request.form['contact']
                query       = db.update(facilities).where(facilities.c.id == fid).values(name=name, hospital_id=hospital_id, description=description, fee=fee, services=services, contact=contact)
                connection.execute(query)
                updateInfo           = db.select([facilities]).where(facilities.c.id == fid)
                update_result        = connection.execute(updateInfo)
                update_row           = update_result.first()
                return render_template('facility_edit.html', id=user_id, role=user_role, row=update_row, facility_id=id, update='Facility Info is Updated', hospitals=hospitals) 
            else:
                count               = len(result)
                if count < 1:
                    return render_template('facility_edit.html', id=user_id, role=user_role, result=result, message='Facility Not Found', facility_id=id, hospitals=hospitals)
                else:
                    row             = result[0]
                    return render_template('facility_edit.html', id=user_id, role=user_role, row=row, facility_id=id, hospitals=hospitals)         
        else:
            return redirect(url_for('logout'))

    else:
        return redirect(url_for('logout'))
    


@app.route('/doctors/edit/<int:id>', methods=['GET', 'POST'])
def doctor_edit(id):
    if 'id' in session and 'role' in session:
        user_id             = session['id']
        user_role           = session['role']
        doctor_id           = id
        if user_role == 'admin':
            metadata            = db.MetaData()
            doctors             = db.Table('doctors', metadata, autoload=True, autoload_with=engine)
            query               = db.select([doctors]).where(doctors.c.id == id)
            result_proxy        = connection.execute(query)
            result              = result_proxy.fetchall()

            # hospitals
            hospitals           = db.Table('hospitals', metadata, autoload=True, autoload_with=engine)
            hospital_query      = db.select([hospitals])
            hospital_result     = connection.execute(hospital_query)
            hospitals       = hospital_result.fetchall()
            if request.method == 'POST':
                did            = request.form['did']
                name           = request.form['name']
                hospital_id    = request.form['hospital_id']
                specialization = request.form['specialization']
                fee            = request.form['fee']
                slots          = request.form['slots']
                description    = request.form['description']
                old_image     = request.form['old_image']
                
                if 'image' in request.files:
                    image           = request.files['image']
                    filename        = secure_filename(image.filename)
                    image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_name  = filename
                else:
                    image_name  = old_image
                query       = db.update(doctors).where(doctors.c.id == did).values(name=name, hospital_id=hospital_id, specialization=specialization, fee=fee, slots=slots, description=description, image=image_name)
                connection.execute(query)
                updateInfo           = db.select([doctors]).where(doctors.c.id == did)
                update_result        = connection.execute(updateInfo)
                update_row           = update_result.first()
                return render_template('doctor_edit.html', id=user_id, role=user_role, row=update_row, doctor_id=id, update='Doctor Info is Updated', hospitals=hospitals) 
            else:
                count               = len(result)
                if count < 1:
                    return render_template('doctor_edit.html', id=user_id, role=user_role, result=result, message='Doctor Not Found', doctor_id=id, hospitals=hospitals)
                else:
                    row             = result[0]
                    return render_template('doctor_edit.html', id=user_id, role=user_role, row=row, doctor_id=id, hospitals=hospitals)         
        else:
            return redirect(url_for('logout'))

    else:
        return redirect(url_for('logout'))


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    session.pop('id', None)
    session.pop('role', None)
    return redirect(url_for('sign_in'))


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html')


if __name__ == '__main__':
    app.run(debug= True)