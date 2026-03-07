import streamlit as st

def listen():
    if "listener_set" not in st.session_state:
        st.session_state.listener_set = True
        st.components.v1.html(
            """
            <script>
            window.addEventListener("message", (event) => {
                if (event.data.type === "move") {
                    fetch("/", {
                        method: "POST",
                        headers: {"Content-Type": "application/json"},
                        body: JSON.stringify(event.data)
                    });
                }
            });
            </script>
            """,
            height=0,
        )
        
