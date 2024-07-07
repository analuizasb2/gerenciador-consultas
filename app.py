from flask import request, redirect, jsonify
from flask_openapi3 import OpenAPI, Info, Tag
from pydantic import BaseModel, validator
from datetime import datetime, timedelta
import requests
import os
from dotenv import load_dotenv

load_dotenv()


info = Info(title="Gerenciador de Consultas", version="1.0.0")
app = OpenAPI(__name__, info=info)

URL_SCHEDULER = "http://agendamento-consultas:3000/agendamentos"
API_KEY = os.getenv('API_KEY')

url = f"https://api.mockaroo.com/api/generate.json?key={API_KEY}&schema=Doctor"
response = requests.get(url)
doctors = response.json()

@app.get('/')
def home():
    """Documentação.
    """
    return redirect('/openapi/swagger')

medicos_tag = Tag(name="Médicos", description="Consulta de médicos")
agendamentos_tag = Tag(name="Agendamentos", description="Agendamento de consultas")

class DoctorPath(BaseModel):
    specialty: str

@app.get('/medicos', tags=[medicos_tag])
def get_doctors_specialty(query: DoctorPath):
    """Médicos por especialidade.
    """
    
    filtered_doctors = [doctor for doctor in doctors if doctor['specialty'] == query.specialty]

    return filtered_doctors

class GetSchedulePath(BaseModel):
    doctor_id: int

@app.get('/horarios', tags=[agendamentos_tag])
def get_schedule_available(query: GetSchedulePath):
    """Consultar horários disponíveis para um médico.
    """    
    slots_available = get_slots_available_doctor(query.doctor_id)

    return slots_available

class PostSchedulePath(BaseModel):
    start_time: str
    doctor_id: int
    patient_id: int
    
    @validator('start_time')
    def check_start_time_format(cls, value):
        try:
            # Attempt to parse the datetime to ensure it's in the correct format
            datetime.strptime(value, '%Y-%m-%d %H:%M')
        except ValueError:
            raise ValueError('start_time must be in the format YYYY-MM-DD HH:MM')
        return value

@app.post('/agendamento', tags=[agendamentos_tag])
def schedule_appointment(body: PostSchedulePath):
    """Agendar uma consulta.
    """

    schedule_body = {
        'start_time': body.start_time,
        'doctor_id': body.doctor_id,
        'patient_id': body.patient_id
    }

    slots_available = get_slots_available_doctor(body.doctor_id)
    if not any(slot['start_time'] == body.start_time for slot in slots_available):
        return jsonify({"error": "Este horário não está mais disponível"}), 400

    try:
        response = requests.post(URL_SCHEDULER, json=schedule_body)
        return response.content, response.status_code, response.headers.items()
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error calling scheduler API: {str(e)}"}), 500

class GetPatientSchedulePath(BaseModel):
    patient_id: int

@app.get('/agendamentos', tags=[agendamentos_tag])
def get_appointments(query: GetPatientSchedulePath):
    """Consultar agendamentos para um paciente.
    """

    response = requests.get(URL_SCHEDULER)
    response_json = response.json()

    appointments_patient = [appointment for appointment in response_json if appointment['patient_id'] == query.patient_id]

    return jsonify({
            "appointments": appointments_patient
        }), 200

class AppointmentIdPath(BaseModel):
    id: int

@app.delete('/agendamento', tags=[agendamentos_tag])
def delete_appointment(query: AppointmentIdPath):
    """Cancelar agendamento.
    """
    
    response = requests.delete(f"{URL_SCHEDULER}?id={query.id}")

    if(response.status_code != 200):
        return jsonify({"error": "Erro ao cancelar agendamento"}), 500

    return jsonify({"message": "Agendamento cancelado com sucesso"}), 200
    
@app.put('/agendamento', tags=[agendamentos_tag])
def update_appointment(query: AppointmentIdPath, body: PostSchedulePath):
    """Atualizar agendamento.
    """

    slots_available = get_slots_available_doctor(body.doctor_id)
    if not any(slot['start_time'] == body.start_time for slot in slots_available):
        return jsonify({"error": "Este horário não está mais disponível para este médico."}), 400
    
    schedule_body = {
        'start_time': body.start_time,
        'doctor_id': body.doctor_id,
        'patient_id': body.patient_id
    }

    try:
        response = requests.put(f"{URL_SCHEDULER}?id={query.id}", json=schedule_body)        
        if(response.status_code != 200):
            return jsonify({"error": "Erro ao atualizar agendamento"}), 500        
        return response.content, response.status_code, response.headers.items()
    
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Error calling scheduler API: {str(e)}"}), 500

def get_slots_available_doctor(id):
    for doctor in doctors: 
        if doctor['doctor_id'] == id:
            selected_doctor = doctor
            
    slots = generate_time_slots(selected_doctor['working_hours_start'], selected_doctor['working_hours_end'])
    response = requests.get(URL_SCHEDULER)
    existing_appointments = response.json()
    slots_available = remove_taken_slots(slots, existing_appointments, doctor_id=id)
    return slots_available

def generate_time_slots(start_time_str, end_time_str, slot_duration=60, days=5):
    start_time = datetime.strptime(start_time_str, '%H:%M:%S').time()
    end_time = datetime.strptime(end_time_str, '%H:%M:%S').time()

    slots = []
    current_date = datetime.now()
    for day in range(days):
        current_date = current_date + timedelta(days=1)
        if current_date.weekday() >= 5:
            continue
        current_time = datetime.combine(current_date, start_time)
        end_time_of_the_day = datetime.combine(current_date, end_time)
        
        while current_time < end_time_of_the_day:
            next_time = current_time + timedelta(minutes=slot_duration)
            if next_time <= end_time_of_the_day:
                slots.append({'start_time': f"{current_time.strftime('%Y-%m-%d %H:%M')}", 'end_time': f"{next_time.strftime('%Y-%m-%d %H:%M')}"})
            current_time = next_time

    return slots

def remove_taken_slots(slots, appointments, doctor_id):
    doctor_appointments = [appointment for appointment in appointments if appointment['doctor_id'] == doctor_id]
    taken_start_times = {datetime.strptime(app['start_time'], '%Y-%m-%d %H:%M') for app in doctor_appointments}   
    available_slots = [slot for slot in slots if datetime.strptime(slot['start_time'], '%Y-%m-%d %H:%M') not in taken_start_times]
    return available_slots