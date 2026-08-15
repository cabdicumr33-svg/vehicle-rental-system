-- Vehicle Rental System - Supabase setup
-- HOW TO RUN:
--   1. Go to your Supabase project -> SQL Editor -> New query
--   2. Paste ALL of this file and click "Run".
--
-- NOTE: This DELETES and recreates the four tables so the app gets the exact
-- schema it needs (all tables are currently empty, so nothing is lost).

-- Delete any old versions of the tables
drop table if exists public.rentals;
drop table if exists public.customers;
drop table if exists public.vehicles;
drop table if exists public.users;

-- Vehicles
create table public.vehicles (
    id bigint generated always as identity primary key,
    name text not null,
    type text not null,
    price numeric not null
);

-- Customers
create table public.customers (
    id bigint generated always as identity primary key,
    name text not null,
    phone text not null
);

-- Rentals (links a customer to a vehicle)
create table public.rentals (
    id bigint generated always as identity primary key,
    customer_id bigint not null references public.customers(id) on delete cascade,
    vehicle_id bigint not null references public.vehicles(id) on delete cascade,
    rental_date date not null,
    return_date date not null,
    total_price numeric not null
);

-- Users (login)
create table public.users (
    id bigint generated always as identity primary key,
    username text not null unique,
    password text not null
);

-- Let the anon key read and write everything
grant usage on schema public to anon;
grant all on table public.vehicles, public.customers, public.rentals, public.users to anon;

-- Turn on row level security and allow the anon key full access
alter table public.vehicles enable row level security;
alter table public.customers enable row level security;
alter table public.rentals enable row level security;
alter table public.users enable row level security;

do $$
declare
    t text;
begin
    foreach t in array array['vehicles', 'customers', 'rentals', 'users'] loop
        execute format(
            'create policy "anon_all" on public.%I as permissive for all to anon using (true) with check (true);',
            t
        );
    end loop;
end $$;

-- Seed sample data (login is admin / admin)
insert into public.users (username, password) values ('admin', 'admin');
insert into public.vehicles (name, type, price) values
    ('Toyota Corolla', 'Sedan', 50),
    ('Honda Civic', 'Sedan', 60),
    ('Ford Mustang', 'Sports Car', 120),
    ('Yamaha Bike', 'Motorcycle', 30);
insert into public.customers (name, phone) values
    ('John Doe', '555-1234'),
    ('Jane Smith', '555-5678');
insert into public.rentals (customer_id, vehicle_id, rental_date, return_date, total_price)
values (1, 1, '2026-08-01', '2026-08-05', 200);