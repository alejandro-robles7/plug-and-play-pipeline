import io
import model
import pandas as pd

data_path = "../data/train"
model_output = "../output"

if __name__ == "__main__":
    my_model = model.train_model(data_path)
    
    model.save_model(model_output, my_model)

    my_model = model.load_model(model_output)

    with open("../../data/smoketest/iris.csv", "r") as file:
        test_data = file.read()
        data_in = io.StringIO(test_data)
        predictions = model.predict(data_in, my_model)
        
        out = io.StringIO()
        pd.DataFrame({'results': predictions}).to_csv(out, header=False, index=False)
        print (out.getvalue())
