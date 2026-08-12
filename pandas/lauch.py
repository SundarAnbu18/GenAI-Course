from langchain_community.document_loaders import CSVLoader
from docs.employee_data import employees
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()


def answer_question_from_csv(csv_file, question):
    loader = CSVLoader(file_path=csv_file)
    data = loader.load()
    model = ChatAnthropic(model="claude-sonnet-5")
    prompt = PromptTemplate(
        template="Use this employee data to answer.\n\n{context}\n\nQuestion: {question}",
        input_variables=["context", "question"],
    )
    context = "\n".join(doc.page_content for doc in data)
    chain = prompt | model
    return chain.invoke({"context": context, "question": question})




print(answer_question_from_csv(employees, "What is the name of the employee with the highest salary?"))
