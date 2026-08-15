import os
import time
from datetime import datetime
from functools import wraps
import httpx
from dotenv import load_dotenv
from flask import Flask, flash, redirect, render_template, request, session, url_for
from supabase import create_client

load_dotenv()

# Supabase connection (set these as environment variables to override)
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL", "https://gwturdqtchawvuoypwmx.supabase.co"
)
SUPABASE_KEY = os.environ.get(
    "SUPABASE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imd3dHVyZHF0Y2hhd3Z1b3lwd214Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODY4MTg0MDMsImV4cCI6MjEwMjM5NDQwM30.oSVBWZ4HpbNlOGpVeykbDx-UomzNfeKT7vf-aQMjyFY",
)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-secret-key")


def retry(query, times=5, delay=1):
    """Run 'query.execute()' and retry if the internet connection drops."""
    for attempt in range(times):
        try:
            return query.execute()
        except httpx.ConnectError:
            if attempt == times - 1:
                raise
            time.sleep(delay)


def days_between(start, end):
    d1 = datetime.strptime(start, "%Y-%m-%d")
    d2 = datetime.strptime(end, "%Y-%m-%d")
    return (d2 - d1).days


# ---------- Login protection ----------

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


# ---------- Authentication ----------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        users = retry(
            supabase.table("users")
            .select("*")
            .eq("username", username)
            .eq("password", password)
        )

        if users.data:
            user = users.data[0]
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session.permanent = bool(request.form.get("remember"))
            flash("Welcome back, " + user["username"] + "!")
            return redirect(url_for("dashboard"))
        flash("Invalid username or password.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- Dashboard ----------

@app.route("/")
@login_required
def dashboard():
    total_vehicles = len(retry(supabase.table("vehicles").select("id")).data)
    total_customers = len(retry(supabase.table("customers").select("id")).data)
    total_rentals = len(retry(supabase.table("rentals").select("id")).data)
    return render_template(
        "dashboard.html",
        total_vehicles=total_vehicles,
        total_customers=total_customers,
        total_rentals=total_rentals,
    )


# ---------- Vehicles ----------

@app.route("/vehicles")
@login_required
def vehicles():
    rows = retry(supabase.table("vehicles").select("*").order("id")).data
    return render_template("vehicles.html", vehicles=rows)


@app.route("/vehicles/new", methods=["GET", "POST"])
@login_required
def vehicle_new():
    if request.method == "POST":
        retry(supabase.table("vehicles").insert({
            "name": request.form["name"],
            "type": request.form["type"],
            "price": float(request.form["price"]),
        }))
        flash("Vehicle added.")
        return redirect(url_for("vehicles"))
    return render_template("vehicle_form.html")


@app.route("/vehicles/<int:id>/edit", methods=["GET", "POST"])
@login_required
def vehicle_edit(id):
    rows = retry(supabase.table("vehicles").select("*").eq("id", id)).data
    if not rows:
        flash("Vehicle not found.")
        return redirect(url_for("vehicles"))
    vehicle = rows[0]

    if request.method == "POST":
        retry(supabase.table("vehicles").update({
            "name": request.form["name"],
            "type": request.form["type"],
            "price": float(request.form["price"]),
        }).eq("id", id))
        flash("Vehicle updated.")
        return redirect(url_for("vehicles"))
    return render_template("vehicle_form.html", vehicle=vehicle)


@app.route("/vehicles/<int:id>/delete", methods=["POST"])
@login_required
def vehicle_delete(id):
    retry(supabase.table("rentals").delete().eq("vehicle_id", id))
    retry(supabase.table("vehicles").delete().eq("id", id))
    flash("Vehicle deleted.")
    return redirect(url_for("vehicles"))


# ---------- Customers ----------

@app.route("/customers")
@login_required
def customers():
    rows = retry(supabase.table("customers").select("*").order("id")).data
    return render_template("customers.html", customers=rows)


@app.route("/customers/new", methods=["GET", "POST"])
@login_required
def customer_new():
    if request.method == "POST":
        retry(supabase.table("customers").insert({
            "name": request.form["name"],
            "phone": request.form["phone"],
        }))
        flash("Customer added.")
        return redirect(url_for("customers"))
    return render_template("customer_form.html")


@app.route("/customers/<int:id>/edit", methods=["GET", "POST"])
@login_required
def customer_edit(id):
    rows = retry(supabase.table("customers").select("*").eq("id", id)).data
    if not rows:
        flash("Customer not found.")
        return redirect(url_for("customers"))
    customer = rows[0]

    if request.method == "POST":
        retry(supabase.table("customers").update({
            "name": request.form["name"],
            "phone": request.form["phone"],
        }).eq("id", id))
        flash("Customer updated.")
        return redirect(url_for("customers"))
    return render_template("customer_form.html", customer=customer)


@app.route("/customers/<int:id>/delete", methods=["POST"])
@login_required
def customer_delete(id):
    retry(supabase.table("rentals").delete().eq("customer_id", id))
    retry(supabase.table("customers").delete().eq("id", id))
    flash("Customer deleted.")
    return redirect(url_for("customers"))


# ---------- Rentals ----------

@app.route("/rentals")
@login_required
def rentals():
    # Get the customer and vehicle names so we can attach them to each rental.
    customer_names = {
        c["id"]: c["name"]
        for c in retry(supabase.table("customers").select("*").order("name")).data
    }
    vehicle_names = {
        v["id"]: v["name"]
        for v in retry(supabase.table("vehicles").select("*").order("name")).data
    }

    rows = retry(supabase.table("rentals").select("*").order("id", desc=True)).data
    rental_list = [
        {
            "id": r["id"],
            "customer_name": customer_names.get(r["customer_id"], "-"),
            "vehicle_name": vehicle_names.get(r["vehicle_id"], "-"),
            "rental_date": r["rental_date"],
            "return_date": r["return_date"],
            "total_price": r["total_price"],
        }
        for r in rows
    ]
    customers_rows = [
        {"id": cid, "name": cname} for cid, cname in customer_names.items()
    ]
    vehicles_rows = [
        {"id": vid, "name": vname} for vid, vname in vehicle_names.items()
    ]
    return render_template(
        "rentals.html",
        rentals=rental_list,
        customers=customers_rows,
        vehicles=vehicles_rows,
    )


@app.route("/rentals/new", methods=["POST"])
@login_required
def rental_new():
    customer_id = request.form["customer_id"]
    vehicle_id = request.form["vehicle_id"]
    rental_date = request.form["rental_date"]
    return_date = request.form["return_date"]

    if not (customer_id and vehicle_id and rental_date and return_date):
        flash("Please fill in all fields.")
        return redirect(url_for("rentals"))

    days = days_between(rental_date, return_date)
    if days < 0:
        flash("Return date must be after the rental date.")
        return redirect(url_for("rentals"))

    vehicle_rows = retry(
        supabase.table("vehicles").select("price").eq("id", vehicle_id)
    ).data
    total = days * vehicle_rows[0]["price"]

    retry(supabase.table("rentals").insert({
        "customer_id": customer_id,
        "vehicle_id": vehicle_id,
        "rental_date": rental_date,
        "return_date": return_date,
        "total_price": total,
    }))
    flash("Rental created.")
    return redirect(url_for("rentals"))


@app.route("/rentals/<int:id>/delete", methods=["POST"])
@login_required
def rental_delete(id):
    retry(supabase.table("rentals").delete().eq("id", id))
    flash("Rental deleted.")
    return redirect(url_for("rentals"))


if __name__ == "__main__":
    app.run(debug=True)