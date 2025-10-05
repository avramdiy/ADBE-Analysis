from flask import Flask, Response, jsonify, request
import pandas as pd
import os
from typing import List

app = Flask(__name__)

# Absolute path to the file containing HTML table(s)
DATA_FILE_PATH = r"C:\Users\avram\OneDrive\Desktop\Bloomtech TRG\TRG Week 44\adbe.us.txt"


def read_tables_from_file(path: str) -> List[pd.DataFrame]:
	"""Read HTML tables from a file and return a list of DataFrames.

	The function uses pandas.read_html which leverages lxml/bs4 under the hood.
	"""
	if not os.path.isfile(path):
		raise FileNotFoundError(f"File not found: {path}")

	# pandas.read_html can accept a file-like object or string containing HTML
	with open(path, "r", encoding="utf-8", errors="ignore") as f:
		content = f.read()

	tables = pd.read_html(content, flavor="bs4")
	return tables


@app.route("/", methods=["GET"])
def index():
	return (
		"<h3>Data API</h3>"
		"<p>Endpoints:</p>"
		"<ul>"
		"<li>/tables - return combined HTML of all tables</li>"
		"<li>/tables/json - return JSON array of tables</li>"
		"</ul>"
	)


@app.route("/health", methods=["GET"])
def health():
	return jsonify({"status": "ok"})


@app.route("/tables", methods=["GET"])
def tables_html():
	"""Return the HTML representation of tables found in the file.

	Optional query param `table` (0-based index) to return a single table.
	"""
	try:
		tables = read_tables_from_file(DATA_FILE_PATH)
	except FileNotFoundError as e:
		return Response(str(e), status=404)
	except ValueError as e:
		# pandas.read_html raises ValueError if no tables found
		return Response(f"No tables found in file: {DATA_FILE_PATH}", status=404)
	except Exception as e:
		return Response(f"Error reading tables: {e}", status=500)

	table_idx = request.args.get("table", default=None, type=int)

	if table_idx is not None:
		if table_idx < 0 or table_idx >= len(tables):
			return Response("table index out of range", status=400)
		html = tables[table_idx].to_html(index=False, border=1)
		return Response(html, mimetype="text/html")

	# Combine all tables into a single HTML response
	html_parts = []
	for i, df in enumerate(tables):
		html_parts.append(f"<h4>Table {i}</h4>")
		html_parts.append(df.to_html(index=False, border=1))

	combined = "\n".join(html_parts)
	return Response(combined, mimetype="text/html")


@app.route("/tables/json", methods=["GET"])
def tables_json():
	"""Return JSON array of tables. Each table is an array of objects (records).

	Optional query param `table` to return a single table as JSON.
	"""
	try:
		tables = read_tables_from_file(DATA_FILE_PATH)
	except FileNotFoundError as e:
		return jsonify({"error": str(e)}), 404
	except ValueError:
		return jsonify({"error": "No tables found in file"}), 404
	except Exception as e:
		return jsonify({"error": f"Error reading tables: {e}"}), 500

	table_idx = request.args.get("table", default=None, type=int)

	if table_idx is not None:
		if table_idx < 0 or table_idx >= len(tables):
			return jsonify({"error": "table index out of range"}), 400
		return jsonify(tables[table_idx].to_dict(orient="records"))

	return jsonify([df.to_dict(orient="records") for df in tables])


if __name__ == "__main__":
	# Development server
	app.run(host="127.0.0.1", port=5000, debug=True)

