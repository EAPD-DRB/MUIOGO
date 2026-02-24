import os
from flask import Blueprint, jsonify, request, session, current_app
from pathlib import Path
from Classes.Base import Config

# Import our new OGCore execution manager
from Classes.Case.OGCoreClass import OGCoreClass

ogcore_api = Blueprint('ogcore_api', __name__)

@ogcore_api.route('/ogcore/run', methods=['POST'])
def run_ogcore():
    """
    Endpoint to trigger an OG-Core model execution.
    Expects JSON payload with the case name andog_spec modifications.
    """
    try:
        data = request.json
        case_name = data.get('case')
        og_spec = data.get('og_spec', {})
        
        if not case_name:
            return jsonify({'error': 'Missing case parameter'}), 400
            
        # Instantiate the runner wrapper
        og_runner = OGCoreClass(case_name, og_spec)
        
        # In a real production app we'd trigger this asynchronously (e.g. via Celery or rq),
        # but for demonstration we'll execute it blockingly.
        # Run Baseline and Reform together to get the compared results.
        og_runner.execute_run(baseline=True, reform=True)
        
        return jsonify({
            'success': True, 
            'message': f'OG-Core execution for {case_name} completed successfully. Outputs and plots generated in DataStorage/{case_name}/res.'
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ogcore_api.route('/ogcore/results', methods=['GET'])
def get_ogcore_results():
    """
    Returns the path or the content of the generated OG-Core output aggregates.
    """
    try:
        case_name = request.args.get('case')
        if not case_name:
            return jsonify({'error': 'Missing case parameter'}), 400
            
        csv_path = Path(Config.DATA_STORAGE, case_name, 'res', 'OG-Core_example_output.csv')
        
        if not csv_path.exists():
            return jsonify({'error': 'Results not found. Have you executed a run?'}), 404
            
        # We can either return the raw CSV or parsed JSON
        # Here we verify existence and return a success notification 
        # that the frontend can use to then fetch the file directly via standard static routing
        return jsonify({
            'success': True,
            'csv_path': str(csv_path),
            'plots_dir': str(Path(Config.DATA_STORAGE, case_name, 'res', 'OG-Core_example_plots'))
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
