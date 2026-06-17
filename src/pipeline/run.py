import argparse
import sys
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

from src.pipeline.flows import process_manifest

def main():
    parser = argparse.ArgumentParser(description="Run the T1D RAG ingestion pipeline.")
    parser.add_argument("--manifest", default="sources.yaml", help="Path to sources manifest YAML")
    parser.add_argument("--smoke-test", action="store_true", help="Process only one document of each type")
    parser.add_argument("--serve", action="store_true", help="Register and serve the flow on the Prefect server")
    parser.add_argument("--path", help="Path of a specific document to ingest")
    
    args = parser.parse_args()
    
    if args.serve:
        print("[INFO] Serving process-manifest flow on local Prefect server...")
        try:
            process_manifest.serve(
                name="t1d-manifest-ingestion",
                parameters={"manifest_path": args.manifest, "limit_one_each": args.smoke_test}
            )
        except Exception as e:
            print(f"[ERROR] Failed to serve flow: {e}")
            sys.exit(1)
    elif args.path:
        print(f"[INFO] Ingesting single document: {args.path}")
        try:
            import yaml
            with open(args.manifest, "r", encoding="utf-8") as f:
                manifest = yaml.safe_load(f)
            found = False
            for collection in manifest.get("collections", []):
                for source in collection.get("sources", []):
                    if source["path"] == args.path:
                        found = True
                        from src.pipeline.flows import process_source
                        count = process_source(source, collection)
                        print(f"[SUCCESS] Ingested {count} chunks successfully for {args.path}")
                        break
                if found:
                    break
            if not found:
                print(f"[ERROR] Path {args.path} not found in manifest")
                sys.exit(1)
        except Exception as e:
            print(f"[ERROR] Single document ingestion failed: {e}")
            sys.exit(1)
    else:
        print(f"[INFO] Running process-manifest flow (smoke_test={args.smoke_test})...")
        try:
            processed = process_manifest(manifest_path=args.manifest, limit_one_each=args.smoke_test)
            print(f"[SUCCESS] Flow run completed. Processed {processed} pending sources.")
        except Exception as e:
            print(f"[ERROR] Flow run failed: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()
