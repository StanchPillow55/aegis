import yaml
import sys

def validate_success_criteria():
    try:
        with open("success_criteria.yaml", "r") as f:
            data = yaml.safe_load(f)
            
        assert isinstance(data, dict), "success_criteria.yaml root must be a dict"
        assert "criteria" in data, "success_criteria.yaml must have a 'criteria' key"
        assert isinstance(data["criteria"], list), "'criteria' must be a list"
        
        for criterion in data["criteria"]:
            assert "id" in criterion, "Missing 'id' field"
            assert "criterion" in criterion, "Missing 'criterion' field"
            assert "verify" in criterion, "Missing 'verify' field"
            assert "pass" in criterion, "Missing 'pass' field"
            assert "artifact" in criterion, "Missing 'artifact' field"
            
        print("success_criteria.yaml OK")
    except Exception as e:
        print(f"ERROR: success_criteria.yaml validation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    validate_success_criteria()
