from flask import Flask, jsonify, abort, request
import os
import json

import base64
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from datetime import datetime

# Create a Flask application instance
app = Flask(__name__)

dns_provider = os.getenv("DNS_PROVIDER", "route53")

def load_acme():
    try:
        with open('/cert/acme.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return jsonify({"error": "File acme.json not found."}), 500
    except json.JSONDecodeError:
        return jsonify({"error": "File acme.json parsing error."}), 500
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500


@app.route("/api/v1/certificates", methods=['GET'])
def list_certificates():
    '''
    Get a list of certificates along with the details
    '''
    if request.headers.get('Accept') != 'application/json':
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = load_acme()
    retval={}
    try:
        for cert in data[dns_provider]["Certificates"]:
            main_domain = cert["domain"]["main"]
        
            
            unbased_cert = base64.b64decode(cert["certificate"])
            loaded_cert = x509.load_pem_x509_certificate(unbased_cert, default_backend())
            
            retval[main_domain] = {
                "subject": loaded_cert.subject.rfc4514_string(),
                "issuer": loaded_cert.issuer.rfc4514_string(),
                "serial_number": loaded_cert.serial_number,
                "not_valid_before": loaded_cert.not_valid_before_utc,
                "not_valid_after": loaded_cert.not_valid_after_utc,
                "not_valid_before_ts": loaded_cert.not_valid_before_utc.timestamp(),
                "not_valid_after_ts": loaded_cert.not_valid_after_utc.timestamp(),
                "version": str(loaded_cert.version),
                "signature_algorithm": loaded_cert.signature_algorithm_oid._name
            }
    except Exception as e:
        return jsonify({"error": "An unexpected error occurred"}), 500
    
    return jsonify(retval)

@app.route("/api/v1/certificate/<cert_main_domain>/<extract>", methods=['GET'])
@app.route("/api/v1/certificate/<cert_main_domain>", defaults={'extract': False}, methods=['GET'])
def get_certificate(cert_main_domain, extract):
    '''
    Get certificate and key
    '''
    if extract is False and request.headers.get('Accept') != 'application/json':
        return jsonify({"error": "Content-Type must be application/json"}), 400
    
    if extract is not False and extract not in ["crt", "key"]:
        return jsonify({"error": "In extraction call last element of a path muyst be crt or key"}), 400

    data = load_acme()
    
    for cert in data["dns_provider"]["Certificates"]:
        if cert["domain"]["main"] == cert_main_domain:
            if extract is False:
                return jsonify({ "cert" : cert["certificate"], "key" : cert["key"]})
            if extract == "crt":
                return base64.b64decode(cert["certificate"])
            if extract == "key":
                return base64.b64decode(cert["key"])
    
    return jsonify({"error": f"Unable to find {cert_main_domain} cert/key"}), 404

